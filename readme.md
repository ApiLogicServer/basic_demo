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

&nbsp;

## What Runs

| Artifact | Description |
|---|---|
| JSON:API | Auto-generated REST for all tables at `/api` |
| Admin UI | Full CRUD at `/admin-app` |
| Business Rules | 5 declarative rules in `logic/logic_discovery/place_order/` - see below |

&nbsp;

## A Brief Look at Rules

Business logic is multi-table derivations and constraints, and actions such as sending email of messsages.  In this application, the logic begins as a prompt shown at the top of this page.

In traditional approaches, business logic is nearly half the effort, with code [like this](logic/procedural/credit_service.py).  This code is about 40X longer tha logic, and hides the intent of the logic.  It was created by (standard) AI by reading the logic.

GenAI-Logic uses AI - with context engineering ([see here](docs/training/logic_bank_api.md)) - to generated ***rules not code*** - [see here](logic/logic_discovery/place_order/).  Key aspects:

1. **Readable:** really just a rigorous translation of our logic.  Because of the LogicBank rule engine, it's fully executable.  Debug it using familiar tools: the debugger, logging, etc
2. **Automatically Runs at Commit Time (no bypass):** Logic Bank listens to SQLAlchemy `before_flush` and runs your logic.  That's why there is no bypsass - all ORM updates are subjected to logic, whether from APIs, message handling, etc.  So, unlike normal code, you *don't call it* - invocation is automatic.
3. **Automatically Ordered:** when the server starts, Logic Bank scans the code under `logic/logic_discovery` and builds internal dependency graphs used to order execution.  This eliminates a key aspect of maintenance: where do I put my new code so it is always run, in the right order.  With rules, put your new rules anywhere.

   * Importantly, dependency management is deterministic.  By contrast, asking AI to generate traditional code is probabalistic which can introduce errors - [see the A/B Test]() [see the A/B test - declarative vs. procedural](logic/procedural/declarative-vs-procedural-comparison.md)


&nbsp;

## Governance Reports

Rules are the most fundamental aspect of governance, but support also includes various reports to help you visualize, manage and test your logic:

| Artifact | Description |
|---|---|
| Logic Diagram | [Rule chain visualization](docs/requirements/logic_flow_basic_demo.md) |
| Governance Report | [Coverage + integrity scores](docs/requirements/health_check.md) |
| Behave Tests | [7 scenarios, 100% pass](test/api_logic_server_behave/reports/Behave%20Logic%20Report.md) |

For more on Governance, [click here](https://apilogicserver.github.io/Docs/IDE-Health-Check/).