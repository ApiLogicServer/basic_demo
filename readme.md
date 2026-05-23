# GenAI-Logic Basic Demo

A complete, auto-generated microservice from a short prompt — explore the API, admin UI, business rules, and governance reports without installing anything beyond Python.

## The Prompt

```
Create a system with customers, orders, items and products.
Include a notes field for orders.

On Placing Orders, Check Credit:
  1. Customer balance must not exceed credit limit
  2. Customer balance = sum of unshipped order totals
  3. Order amount_total = sum of item amounts
  4. Item amount = quantity × unit_price
  5. Item unit_price copied from Product

Use case: App Integration
  1. Publish Order to Kafka topic 'order_shipping' when shipped
```

## Run It

```bash
git clone <repo>
cd basic_demo
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python api_logic_server_run.py
```

Then open: http://localhost:5656

Security is not enabled, so no login is required.

## What's Included

| Artifact | Description |
|---|---|
| JSON:API | Auto-generated REST for all tables at `/api` |
| Admin UI | Full CRUD at `/admin-app` |
| Business Rules | 5 declarative rules in `logic/logic_discovery/place_order/` (vs 200 lines of code - see [declarative vs. procedural](logic/declarative-vs-procedural-comparison.html)) |
| Logic Diagram | [Rule chain visualization](docs/requirements/logic_flow_basic_demo.md) |
| Governance Report | [Coverage + integrity scores](docs/requirements/health_check.md) |
| Behave Tests | [7 scenarios, 100% pass](test/api_logic_server_behave/reports/Behave%20Logic%20Report.md) |

For more on Governance, [click here](https://apilogicserver.github.io/Docs/IDE-Health-Check/).