from odoo.orm.fields._field_setup import _normalize_computed_attrs

INHERITED_COMPUTE = {"compute": "_compute_company_id", "store": True, "readonly": False}


def normalized(**override):
    attrs = {**INHERITED_COMPUTE, **override}
    _normalize_computed_attrs(attrs)
    return attrs


def test_a_related_override_of_a_computed_field_is_sudoed_like_any_related():
    attrs = normalized(related="category_id.company_id", store=False)
    assert attrs["compute_sudo"] is True


def test_a_related_override_still_honours_related_sudo_false():
    attrs = normalized(
        related="category_id.company_id", store=False, related_sudo=False
    )
    assert attrs["compute_sudo"] is False


def test_a_plain_related_and_a_related_override_normalize_alike():
    plain = {"related": "category_id.company_id"}
    _normalize_computed_attrs(plain)
    override = normalized(related="category_id.company_id", store=False, readonly=True)
    for name in ("store", "compute_sudo", "copy", "readonly"):
        assert override[name] == plain[name], name


def test_a_compute_without_related_keeps_its_own_defaults():
    attrs: dict[str, object] = {"compute": "_compute_x"}
    _normalize_computed_attrs(attrs)
    assert attrs["compute_sudo"] is False
    assert attrs["readonly"] is True
