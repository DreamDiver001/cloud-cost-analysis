"""Synthetic cloud billing data for a fictional pharma company, using FOCUS 1.x column names.

Six months (May-October 2026), AWS and Azure. Built-in situations the analysis should find:
untagged spend, a GPU cost spike in August, dev machines that never switch off,
a growing data lake, and an Azure reservation that is only partly used.
"""
import calendar
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = date(2026, 5, 1), date(2026, 10, 31)

SERVICES = {
    "AWS": {
        "compute": ("Amazon Elastic Compute Cloud", "Compute", "Hours", 0.42),
        "storage": ("Amazon Simple Storage Service", "Storage", "GB-Mo", 0.023),
        "db": ("Amazon Relational Database Service", "Databases", "Hours", 0.95),
        "ml": ("Amazon SageMaker", "AI and Machine Learning", "Hours", 32.77),
        "net": ("AWS Data Transfer", "Networking", "GB", 0.09),
        "analytics": ("Amazon Athena", "Analytics", "TB", 5.0),
    },
    "Microsoft": {
        "compute": ("Virtual Machines", "Compute", "Hours", 0.38),
        "storage": ("Storage", "Storage", "GB-Mo", 0.021),
        "db": ("Azure SQL Database", "Databases", "Hours", 1.10),
        "ml": ("Azure Machine Learning", "AI and Machine Learning", "Hours", 27.20),
        "net": ("Bandwidth", "Networking", "GB", 0.087),
        "analytics": ("Azure Synapse Analytics", "Analytics", "TB", 5.0),
    },
}
REGIONS = {"AWS": ("eu-west-1", "Europe (Ireland)"), "Microsoft": ("westeurope", "West Europe")}
ACCOUNTS = {
    "AWS": ("111122223333", "Helix Pharma AWS"),
    "Microsoft": ("enrollment-4410", "Helix Pharma Azure EA"),
}

COMMITMENTS = {
    "AWS": {"id": "sp-0a1b2c3d", "name": "Compute Savings Plan 1yr", "type": "Savings Plan",
            "monthly_fee": 12000.0, "discount": 0.28},
    "Microsoft": {"id": "ri-7f8e9d10", "name": "VM Reserved Instances 1yr", "type": "Reservation",
                  "monthly_fee": 9000.0, "discount": 0.40},
}


@dataclass
class Resource:
    provider: str
    sub_account: str
    kind: str
    name: str
    daily: float
    pattern: str
    tags: dict
    eligible: bool = False

    @property
    def id(self):
        return f"{self.provider[:3].lower()}-{self.sub_account}-{self.name}"


def build_resources(rng: random.Random) -> list[Resource]:
    res = []

    def add(provider, sub, kind, name, daily, pattern, bu, env, app, owner, tagged=True, eligible=False):
        tags = {"business_unit": bu, "environment": env, "application": app, "owner": owner} if tagged else (
            {"environment": env} if rng.random() < 0.5 else {})
        res.append(Resource(provider, sub, kind, name, daily, pattern, tags, eligible))

    for i in range(6):
        add("AWS", "rnd-prod", "compute", f"lims-app-{i}", 210 + 20 * i, "prod", "R&D", "prod", "LIMS", "rnd-platform", eligible=True)
    for i in range(3):
        add("AWS", "rnd-prod", "db", f"lims-db-{i}", 180, "prod", "R&D", "prod", "LIMS", "rnd-platform")
    add("AWS", "rnd-prod", "ml", "genomics-training", 900, "gpu", "R&D", "prod", "Genomics ML", "data-science")
    add("AWS", "rnd-prod", "storage", "genomics-raw", 260, "growth_slow", "R&D", "prod", "Genomics ML", "data-science")
    for i in range(4):
        add("AWS", "rnd-dev", "compute", f"rnd-dev-vm-{i}", 95, "scheduled", "R&D", "dev", "LIMS", "rnd-platform")

    for i in range(5):
        add("AWS", "mfg-prod", "compute", f"mes-app-{i}", 180, "prod", "Manufacturing", "prod", "MES", "mfg-it", eligible=True)
    add("AWS", "mfg-prod", "storage", "plant-datalake", 420, "growth_fast", "Manufacturing", "prod", "Plant Data Lake", "mfg-data")
    add("AWS", "mfg-prod", "analytics", "plant-analytics", 160, "prod", "Manufacturing", "prod", "Plant Data Lake", "mfg-data")
    add("AWS", "mfg-prod", "net", "plant-transfer", 110, "prod", "Manufacturing", "prod", "MES", "mfg-it")

    for i in range(4):
        add("Microsoft", "commercial-prod", "compute", f"crm-vm-{i}", 170, "prod", "Commercial", "prod", "CRM", "commercial-it")
    add("Microsoft", "commercial-prod", "db", "crm-sql", 240, "prod", "Commercial", "prod", "CRM", "commercial-it")
    add("Microsoft", "commercial-prod", "analytics", "sales-synapse", 210, "prod", "Commercial", "prod", "Sales Analytics", "commercial-data")
    for i in range(5):
        add("Microsoft", "commercial-dev", "compute", f"crm-dev-vm-{i}", 85, "always_on", "Commercial", "dev", "CRM", "commercial-it")

    for i in range(3):
        add("Microsoft", "corp-shared", "compute", f"intranet-vm-{i}", 120, "prod", "Corporate IT", "prod", "Intranet", "corp-it", eligible=True)
    add("Microsoft", "corp-shared", "storage", "backup-vault", 150, "growth_slow", "Corporate IT", "prod", "Backup", "corp-it")
    add("Microsoft", "corp-shared", "net", "corp-bandwidth", 70, "prod", "Corporate IT", "prod", "Network", "corp-it")
    for i in range(6):
        add("Microsoft", "sandbox", "compute", f"sandbox-vm-{i}", 75, "always_on", "", "dev", "", "", tagged=False)
    for i in range(3):
        add("AWS", "sandbox", "compute", f"poc-instance-{i}", 90, "always_on", "", "dev", "", "", tagged=False)
    add("AWS", "sandbox", "ml", "notebook-gpu", 140, "always_on", "", "dev", "", "", tagged=False)
    add("AWS", "sandbox", "storage", "old-exports", 65, "flat", "", "dev", "", "", tagged=False)
    return res


def daily_list_cost(r: Resource, d: date, rng: random.Random) -> float:
    days = (d - START).days
    weekend = d.weekday() >= 5
    noise = rng.uniform(0.95, 1.05)
    if r.pattern == "prod":
        factor = 0.85 if weekend else 1.0
    elif r.pattern == "scheduled":
        factor = 0.1 if weekend else 1.0
    elif r.pattern in ("always_on", "flat"):
        factor = 1.0
    elif r.pattern == "growth_fast":
        factor = 1.002 ** days
    elif r.pattern == "growth_slow":
        factor = 1.0005 ** days
    elif r.pattern == "gpu":
        factor = (0.3 if weekend else rng.uniform(0.6, 1.4))
        if date(2026, 8, 11) <= d <= date(2026, 8, 19):
            factor += 3.1
    else:
        factor = 1.0
    return round(r.daily * factor * noise, 2)


def row(r_provider, sub, d, *, category, description, frequency, resource_id="", resource_name="", kind=None,
        pricing="Standard", commitment=None, status="", list_cost=0.0, billed=0.0, effective=0.0, tags=None):
    service, svc_cat, unit, unit_price = SERVICES[r_provider][kind] if kind else ("", "", "", 1)
    acc_id, acc_name = ACCOUNTS[r_provider]
    month_start = d.replace(day=1)
    month_end = d.replace(day=calendar.monthrange(d.year, d.month)[1]) + timedelta(days=1)
    return {
        "BillingAccountId": acc_id, "BillingAccountName": acc_name, "BillingCurrency": "USD",
        "BillingPeriodStart": month_start.isoformat(), "BillingPeriodEnd": month_end.isoformat(),
        "ChargePeriodStart": d.isoformat(), "ChargePeriodEnd": (d + timedelta(days=1)).isoformat(),
        "ChargeCategory": category, "ChargeDescription": description, "ChargeFrequency": frequency,
        "ProviderName": r_provider, "InvoiceIssuerName": r_provider,
        "SubAccountId": f"{r_provider[:3].lower()}-{sub}", "SubAccountName": sub,
        "RegionId": REGIONS[r_provider][0], "RegionName": REGIONS[r_provider][1],
        "ResourceId": resource_id, "ResourceName": resource_name, "ServiceName": service, "ServiceCategory": svc_cat,
        "PricingCategory": pricing,
        "CommitmentDiscountId": commitment["id"] if commitment else "",
        "CommitmentDiscountName": commitment["name"] if commitment else "",
        "CommitmentDiscountType": commitment["type"] if commitment else "",
        "CommitmentDiscountStatus": status,
        "ConsumedQuantity": round(list_cost / unit_price, 3) if kind and list_cost else "",
        "ConsumedUnit": unit,
        "ListCost": round(list_cost, 2), "BilledCost": round(billed, 2), "EffectiveCost": round(effective, 2),
        "Tags": json.dumps(tags or {}),
    }


def main():
    rng = random.Random(7)
    resources = build_resources(rng)
    rows = []
    d = START
    while d <= END:
        dim = calendar.monthrange(d.year, d.month)[1]
        for provider, c in COMMITMENTS.items():
            if d.day == 1:
                rows.append(row(provider, "corp-shared", d, category="Purchase", description=f"{c['name']} monthly fee",
                                frequency="Recurring", commitment=c, billed=c["monthly_fee"], effective=0.0,
                                tags={"business_unit": "Corporate IT", "environment": "shared"}))

            costs = {r.id: daily_list_cost(r, d, rng) for r in resources if r.provider == provider}
            eligible = [r for r in resources if r.provider == provider and r.eligible]
            eligible_list = sum(costs[r.id] for r in eligible)
            daily_commit = c["monthly_fee"] / dim
            capacity_list = daily_commit / (1 - c["discount"])
            covered_list = min(eligible_list, capacity_list)
            share = covered_list / eligible_list if eligible_list else 0

            for r in resources:
                if r.provider != provider:
                    continue
                lc = costs[r.id]
                common = dict(resource_id=r.id, resource_name=r.name, kind=r.kind, tags=r.tags)
                if r.eligible and share > 0:
                    committed = lc * share
                    rows.append(row(provider, r.sub_account, d, category="Usage", description=f"{r.name} usage",
                                    frequency="Usage-Based", pricing="Committed", commitment=c, status="Used",
                                    list_cost=committed, billed=0.0, effective=committed * (1 - c["discount"]), **common))
                    lc -= committed
                if lc > 0.004:
                    rows.append(row(provider, r.sub_account, d, category="Usage", description=f"{r.name} usage",
                                    frequency="Usage-Based", list_cost=lc, billed=lc, effective=lc, **common))

            unused = daily_commit - covered_list * (1 - c["discount"])
            if unused > 0.004:
                rows.append(row(provider, "corp-shared", d, category="Usage", description=f"{c['name']} unused commitment",
                                frequency="Usage-Based", resource_id=c["id"], resource_name=c["name"], pricing="Committed",
                                commitment=c, status="Unused", effective=unused,
                                tags={"business_unit": "Corporate IT", "environment": "shared"}))

        if d == date(2026, 7, 15):
            rows.append(row("AWS", "corp-shared", d, category="Credit", description="AWS promotional credit",
                            frequency="One-Time", billed=-2000.0, effective=-2000.0,
                            tags={"business_unit": "Corporate IT", "environment": "shared"}))
        d += timedelta(days=1)

    out = ROOT / "data" / "focus_billing.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
