# GenAI-Logic Basic Demo

A working microservice — API, admin UI, and business rules — generated from a short prompt. The goal is to show how **declarative rules** address the governance problem at the core of enterprise logic.

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

Then open: http://localhost:5656 (no login required — security is disabled in this demo).

&nbsp;

## What Runs

| Artifact | Description |
|---|---|
| JSON:API | Auto-generated REST for all tables at `/api` |
| Admin UI | Full CRUD at `/admin-app` |
| Business Rules | 5 declarative rules in `logic/logic_discovery/place_order/` |

&nbsp;

## Why Rules Matter

Business logic — multi-table derivations, constraints, and side-effects like messaging — is typically **40–50% of coding and debugging effort**. Versata measured this across production deployments: declarative rules required writing only 3% of equivalent procedural code.

Standard AI can generate procedural code: here is [what Copilot produced](logic/procedural/credit_service.py) from the same requirements above — **204 lines, with 2 subtle bugs** (documented in the [A/B comparison](logic/procedural/declarative-vs-procedural-comparison.md)).

GenAI-Logic uses context engineering to make AI generate **rules instead**: [5 executable lines](logic/logic_discovery/place_order/check_credit.py).

The reduction matters because of these structural properties:

| Property | Procedural Code | Declarative Rules |
|---|---|---|
| **Readability** | Intent buried in implementation — maintainers see *how*, not *what* | **Direct translation of requirements** — intent visible without tracing code |
| **Correctness** | [A/B test](logic/procedural/declarative-vs-procedural-comparison.md) uncovered 2 bugs in Copilot-generated code | **Automatic reuse over all change paths** (insert, update, delete, FK reassignment) |
| **Maintainability** | Adding logic requires finding every call site and insertion point | **Auto-ordered** at startup via dependency graph — add a rule anywhere, engine places it correctly |
| **Enforcement** | Must be explicitly called — can be bypassed or forgotten | **No bypass** — listens to `before_flush`, every ORM write runs rules automatically |

These properties are what make rules a governance mechanism, not just a style preference.

&nbsp;

## Governance Reports

Rules are the foundation, but governance also requires visibility — that the logic is correct, complete, and tested. These reports provide that. And because rules are structured and machine-readable, the system can generate tests directly from them — a downstream consequence of the rules themselves being unambiguous:

| Artifact | Description |
|---|---|
| Logic Diagram | [Requirements, logic diagram, and rules summary](docs/requirements/logic_flow_basic_demo.md) |
| Governance Report | [Coverage + integrity scores](docs/requirements/health_check.md) |
| Behave Tests | [7 scenarios, 100% pass — generated from the rules](test/api_logic_server_behave/reports/Behave%20Logic%20Report.md) |

For more on Governance, [click here](https://apilogicserver.github.io/Docs/IDE-Health-Check/).
