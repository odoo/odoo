# Test Case Pattern

**Purpose:** Write automated tests for Odoo models, business logic, and HTTP endpoints using the built-in unittest-based framework. Each test runs inside a database transaction that is rolled back after the test, keeping the database clean.

**Source:** `odoo/tests/common.py` (lines 302, 990, 1171, 1251, 2196), `addons/base_address_extended/tests/test_street_fields.py`, `addons/account/tests/test_account_journal.py`

---

## When to Use

- Testing model methods, computed fields, and constraints
- Verifying business workflows (create → confirm → invoice)
- Testing HTTP routes and portal pages (`HttpCase`)
- Running browser-based UI tours (`HttpCase.start_tour`)

---

## Base Test Classes

```
odoo.tests.common.TransactionCase     # Most common: one DB transaction per test method, rolled back after
odoo.tests.common.SingleTransactionCase  # All methods share one transaction (faster, less isolation)
odoo.tests.common.HttpCase            # Extends TransactionCase; spins up an HTTP server for route/tour tests
```

---

## TransactionCase — Unit / Integration Tests

```python
# addons/base_address_extended/tests/test_street_fields.py
from odoo.tests.common import TransactionCase


class TestStreetFields(TransactionCase):
    """No setUpClass needed for simple cases — self.env is available directly."""

    def test_partner_create(self):
        """Test compute and inverse methods on street fields."""
        mx_id = self.env.ref('base.mx').id          # resolve XML ID to record ID
        partner = self.env['res.partner'].create({
            'name': 'Test Address',
            'country_id': mx_id,
        })

        partner.street = 'Chaussee de Namur 40a - 2b'
        self.assertEqual(partner.street_name, 'Chaussee de Namur')
        self.assertEqual(partner.street_number, '40a')
        self.assertEqual(partner.street_number2, '2b')

    def test_child_sync(self):
        """Test that city_id propagates to contact-type children."""
        usa = self.env.ref('base.us')
        city = self.env['res.city'].create({'name': 'New York', 'country_id': usa.id})
        parent = self.env['res.partner'].create({
            'name': 'Parent Company',
            'country_id': usa.id,
            'city_id': city.id,
        })
        child = self.env['res.partner'].create({
            'name': 'Child Contact',
            'type': 'contact',
            'parent_id': parent.id,
        })
        # assertRecordValues checks multiple field values on multiple records at once
        self.assertRecordValues(child, [{
            'name': 'Child Contact',
            'country_id': usa.id,
            'city_id': city.id,
        }])
```

---

## setUpClass — Shared Fixtures

```python
# addons/account/tests/test_account_journal.py
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, HttpCase
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')   # run after install, not during
class TestAccountJournal(AccountTestInvoicingCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        """Runs once before all test methods in this class.
        Use for expensive setup: creating companies, currencies, base records."""
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.company_data_2 = cls.setup_other_company()

    def test_constraint_currency_consistency(self):
        journal = self.company_data['default_journal_bank']
        journal.currency_id = self.other_currency

        with self.assertRaises(ValidationError):
            journal.default_account_id.currency_id = self.company_data['currency']

    def test_changing_journal_company(self):
        self.company_data['default_journal_sale'].code = "DIFFERENT"
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        with self.assertRaisesRegex(UserError, "entries linked to it"):
            self.company_data['default_journal_sale'].company_id = \
                self.company_data_2['company']
```

---

## @tagged Decorator

```python
from odoo.tests import tagged

@tagged('post_install', '-at_install')   # run post-install, skip at-install
@tagged('my_feature')                    # custom tag for selective runs
class MyTest(TransactionCase):
    ...
```

Built-in tags:

| Tag | Meaning |
|-----|---------|
| `at_install` | Run when the module is being installed (default) |
| `-at_install` | Skip during install |
| `post_install` | Run after all modules are installed |
| `standard` | Included in standard test run |
| `slow` | Excluded from standard run unless explicitly requested |

Run selectively:
```bash
python odoo-bin -d mydb --test-tags my_feature
python odoo-bin -d mydb --test-tags /account  # all tests in the account addon
```

---

## HttpCase — Route and Tour Tests

```python
from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestWebsiteFlow(HttpCase):

    def test_01_checkout_tour(self):
        """Run a browser-driven JavaScript tour."""
        self.start_tour('/web', 'my_addon.my_tour_name', login='admin')

    def test_route_response(self):
        """Make an authenticated HTTP request and check the response."""
        self.authenticate('admin', 'admin')
        response = self.url_open('/my/route?param=value')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'expected content', response.content)
```

---

## Common Assertion Methods

| Method | Purpose |
|--------|---------|
| `assertEqual(a, b)` | Exact equality |
| `assertNotEqual(a, b)` | Inequality |
| `assertTrue(x)` / `assertFalse(x)` | Boolean check |
| `assertRaises(ExcClass)` | Context manager: expect exception |
| `assertRaisesRegex(ExcClass, pattern)` | Expect exception with message matching regex |
| `assertRecordValues(records, list_of_dicts)` | Odoo-specific: compare field values on a recordset |
| `assertIn(member, container)` | Membership check |
| `env.ref('xml.id')` | Resolve XML ID to record |

---

## Test File Placement

```
addons/my_addon/
└── tests/
    ├── __init__.py          # imports all test modules
    ├── common.py            # shared base class with setUpClass fixtures
    ├── test_my_model.py     # unit tests for model logic
    ├── test_my_workflow.py  # integration tests across multiple models
    └── test_my_routes.py    # HttpCase tests for controllers
```

```python
# tests/__init__.py
from . import test_my_model
from . import test_my_workflow
from . import test_my_routes
```

---

## Common Pitfalls

- **`setUpClass` data is shared across all test methods** in the class. Mutating it in one test contaminates others. Use `setUp` (per-method) for mutable fixtures, or restore state explicitly.
- **`self.env` uses the test user's environment.** To test access control, switch user: `self.env['my.model'].with_user(self.other_user).read([])`.
- **`@tagged('-at_install')` is required for tests that depend on other addons** being fully installed (e.g., tests using `account` records in a module that depends on `account`).
- **`assertRaises` must be used as a context manager** (`with self.assertRaises(...):`) — calling it without `with` does not catch anything.
- **Creating records in `setUpClass` requires `cls.env`**, not `self.env`. The class-level env shares the outer transaction savepoint.
- **Tours require a running HTTP server** — `HttpCase` starts one automatically, but the test must be tagged `post_install` so the full asset bundle is compiled.

---

## Related Patterns

- [orm-model-pattern.md](./orm-model-pattern.md) — models being tested
- [api-decorator-pattern.md](./api-decorator-pattern.md) — constraints tested with `assertRaises(ValidationError)`
- [security-model-pattern.md](./security-model-pattern.md) — access errors tested with `assertRaises(AccessError)`
- [http-controller-pattern.md](./http-controller-pattern.md) — routes tested with `HttpCase`
