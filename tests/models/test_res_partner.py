"""Database-free tests for ``res.partner`` model methods.

Covers compute methods, address parsing, and pure business logic.
Many2one traversal (``parent_id``, ``country_id``) works through
DictBackend.

Run with::

    python -m pytest core/tests/models/test_res_partner.py -v
"""

import pytest

# ── _compute_display_name ────────────────────────────────────────


class TestDisplayName:
    """``_compute_display_name``: the most-overridden method in Odoo."""

    def test_individual(self, make_partner):
        p = make_partner("Alice")
        p._compute_display_name()
        assert p.display_name == "Alice"

    def test_company(self, make_company_partner):
        p = make_company_partner("Acme Corp")
        p._compute_display_name()
        assert p.display_name == "Acme Corp"

    def test_company_contact(self, make_company_partner, make_partner):
        """Contact under a company: 'Company, Contact'."""
        company = make_company_partner("Acme Corp")
        contact = make_partner(
            "Bob", parent_id=company.id, company_name="Acme Corp"
        )
        contact._compute_display_name()
        assert contact.display_name == "Acme Corp, Bob"

    def test_empty_name(self, env):
        """Partner with no name falls back gracefully."""
        partner = env["res.partner"].create({"is_company": False})
        partner._compute_display_name()
        assert partner.display_name is not None

    def test_special_characters(self, make_partner):
        p = make_partner("Jose Maria O'Brien-Garcia")
        p._compute_display_name()
        assert p.display_name == "Jose Maria O'Brien-Garcia"

    def test_whitespace_stripped(self, make_partner):
        p = make_partner("  Alice  ")
        p._compute_display_name()
        assert p.display_name == "Alice"

    def test_batch_compute(self, env):
        """Compute works on multi-record recordsets."""
        Partner = env["res.partner"]
        p1 = Partner.create({"name": "Alice"})
        p2 = Partner.create({"name": "Bob"})
        (p1 | p2)._compute_display_name()
        assert p1.display_name == "Alice"
        assert p2.display_name == "Bob"


# ── _compute_complete_name ───────────────────────────────────────


class TestCompleteName:
    """``_compute_complete_name``: hierarchical name with company."""

    def test_standalone_company(self, make_company_partner):
        company = make_company_partner("Acme Corp")
        company._compute_complete_name()
        assert company.complete_name == "Acme Corp"

    def test_contact_under_company(self, make_company_partner, make_partner):
        company = make_company_partner("Acme Corp")
        contact = make_partner(
            "Alice", parent_id=company.id, company_name="Acme Corp",
        )
        # commercial_company_name is needed by _get_complete_name
        contact._compute_commercial_partner()
        contact._compute_commercial_company_name()
        contact._compute_complete_name()
        assert "Acme Corp" in contact.complete_name
        assert "Alice" in contact.complete_name

    def test_standalone_person(self, make_partner):
        p = make_partner("Freelancer")
        p._compute_complete_name()
        assert p.complete_name == "Freelancer"

    def test_person_with_company_name(self, make_partner):
        """Person with company_name but no parent_id."""
        p = make_partner("Alice", company_name="Acme")
        p._compute_commercial_partner()
        p._compute_commercial_company_name()
        p._compute_complete_name()
        assert "Acme" in p.complete_name
        assert "Alice" in p.complete_name


# ── _compute_email_formatted ─────────────────────────────────────


class TestEmailFormatted:
    """``_compute_email_formatted``: RFC 5322 formatted email."""

    def test_name_and_email(self, make_partner):
        p = make_partner("Alice", email="alice@example.com")
        p._compute_email_formatted()
        assert "Alice" in p.email_formatted
        assert "alice@example.com" in p.email_formatted

    def test_email_only(self, env):
        p = env["res.partner"].create({"email": "bob@example.com"})
        p._compute_email_formatted()
        assert "bob@example.com" in p.email_formatted

    def test_no_email(self, make_partner):
        p = make_partner("Charlie")
        p._compute_email_formatted()
        assert not p.email_formatted

    def test_email_normalization(self, make_partner):
        p = make_partner("Alice", email="Alice@Example.COM")
        p._compute_email_formatted()
        assert "alice@example.com" in p.email_formatted

    def test_false_name_no_literal_false(self, env):
        """name=False must not produce literal 'False' in output."""
        p = env["res.partner"].create({"email": "user@example.com"})
        p._compute_email_formatted()
        assert "False" not in str(p.email_formatted)


# ── _compute_company_type ────────────────────────────────────────


class TestCompanyType:
    """``_compute_company_type``: is_company bool to selection."""

    def test_company(self, make_company_partner):
        p = make_company_partner()
        p._compute_company_type()
        assert p.company_type == "company"

    def test_person(self, make_partner):
        p = make_partner()
        p._compute_company_type()
        assert p.company_type == "person"

    def test_default_is_person(self, env):
        p = env["res.partner"].create({"name": "Default"})
        p._compute_company_type()
        assert p.company_type == "person"


# ── _compute_commercial_partner ──────────────────────────────────


class TestCommercialPartner:
    """``_compute_commercial_partner``: finds the top-level company."""

    def test_company_is_self(self, make_company_partner):
        company = make_company_partner("Acme")
        company._compute_commercial_partner()
        assert company.commercial_partner_id == company

    def test_contact_gets_parent(self, make_company_partner, make_partner):
        company = make_company_partner("Acme")
        company._compute_commercial_partner()
        contact = make_partner("Bob", parent_id=company.id)
        contact._compute_commercial_partner()
        assert contact.commercial_partner_id == company

    def test_standalone_person_is_self(self, make_partner):
        person = make_partner("Freelancer")
        person._compute_commercial_partner()
        assert person.commercial_partner_id == person


# ── _compute_tz_offset ───────────────────────────────────────────


class TestTzOffset:
    """``_compute_tz_offset``: timezone to UTC offset string."""

    def test_utc(self, make_partner):
        p = make_partner(tz="GMT")
        p._compute_tz_offset()
        assert p.tz_offset == "+0000"

    def test_no_timezone(self, make_partner):
        p = make_partner()
        p._compute_tz_offset()
        # Falls back to GMT → "+0000"
        assert p.tz_offset == "+0000"

    def test_positive_offset(self, make_partner):
        p = make_partner(tz="Asia/Tokyo")
        p._compute_tz_offset()
        assert p.tz_offset == "+0900"

    def test_negative_offset(self, make_partner):
        p = make_partner(tz="US/Pacific")
        p._compute_tz_offset()
        # -0800 or -0700 depending on DST
        assert p.tz_offset.startswith("-0")


# ── _compute_type_address_label ──────────────────────────────────


class TestTypeAddressLabel:
    """``_compute_type_address_label``: type-based label string."""

    def test_invoice(self, env):
        addr = env["res.partner"].create({"name": "Billing", "type": "invoice"})
        addr._compute_type_address_label()
        assert "Invoice" in addr.type_address_label

    def test_delivery(self, env):
        addr = env["res.partner"].create({"name": "Warehouse", "type": "delivery"})
        addr._compute_type_address_label()
        assert "Delivery" in addr.type_address_label

    def test_contact_with_parent(self, make_company_partner, make_partner):
        parent = make_company_partner("Corp")
        contact = make_partner("Employee", type="contact", parent_id=parent.id)
        contact._compute_type_address_label()
        assert "Company" in contact.type_address_label

    def test_standalone_contact(self, make_partner):
        p = make_partner("Solo", type="contact")
        p._compute_type_address_label()
        assert "Address" in p.type_address_label


# ── _get_street_split ────────────────────────────────────────────


class TestStreetSplit:
    """``_get_street_split``: regex-based street address parser."""

    def test_name_and_number(self, make_partner):
        p = make_partner(street="Keizersgracht 42")
        result = p._get_street_split()
        assert result["street_name"] == "Keizersgracht"
        assert result["street_number"] == "42"

    def test_name_only(self, make_partner):
        p = make_partner(street="Oak Avenue")
        result = p._get_street_split()
        assert result["street_name"] == "Oak Avenue"
        assert result["street_number"] == ""

    def test_empty_street(self, make_partner):
        p = make_partner(street="")
        result = p._get_street_split()
        assert result["street_name"] == ""

    def test_alphanumeric_house_number(self, make_partner):
        p = make_partner(street="Keizersgracht 42a")
        result = p._get_street_split()
        assert result["street_name"] == "Keizersgracht"
        assert result["street_number"] == "42a"


# ── Many2one traversal ───────────────────────────────────────────


class TestMany2oneTraversal:
    """Many2one field access through DictBackend."""

    def test_parent_name(self, make_company_partner, make_partner):
        parent = make_company_partner("Parent Corp")
        child = make_partner("Child", parent_id=parent.id)
        assert child.parent_id.name == "Parent Corp"

    def test_empty_many2one(self, make_partner):
        p = make_partner("Solo")
        assert not p.parent_id
        assert len(p.parent_id) == 0

    def test_chain_traversal(self, make_company_partner, make_partner):
        """M2O chain: child → parent (company) is its own commercial partner."""
        parent = make_company_partner("Parent Corp")
        parent._compute_commercial_partner()
        child = make_partner("Child", parent_id=parent.id)
        child._compute_commercial_partner()
        # Child's commercial partner is the nearest company ancestor
        assert child.commercial_partner_id == parent
