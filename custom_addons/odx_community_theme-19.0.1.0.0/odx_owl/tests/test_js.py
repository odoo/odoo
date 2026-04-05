import os

import odoo

from odoo.addons.web.tests.test_js import unit_test_error_checker


SUITE_PATHS = [
    "@odx_owl/components/tabs",
    "@odx_owl/components/checkbox",
    "@odx_owl/components/select",
    "@odx_owl/components/calendar",
    "@odx_owl/components/radio_group",
    "@odx_owl/components/toggle_group",
    "@odx_owl/components/accordion",
    "@odx_owl/components/input_otp",
    "@odx_owl/components/slider",
    "@odx_owl/components/calendar_range",
    "@odx_owl/components/progress",
    "@odx_owl/components/dialog",
    "@odx_owl/components/alert_dialog",
    "@odx_owl/components/popover",
]


def _generate_hash(test_string):
    hash_value = 0
    for char in test_string:
        hash_value = (hash_value << 5) - hash_value + ord(char)
        hash_value &= 0xFFFFFFFF
    return f"{hash_value:08x}"


def _get_parametric_hoot_filters(test_params):
    filters = []
    for sign, param in test_params:
        parts = param.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_sign = sign
            if part.startswith("-"):
                part = part[1:]
                part_sign = "-" if sign == "+" else "+"
            filters.append((part_sign, part))

    hoot_filters = ""
    for sign, descriptor in sorted(filters):
        hashed = _generate_hash(descriptor)
        if sign == "-":
            hashed = f"-{hashed}"
        hoot_filters += f"&id={hashed}"
    return hoot_filters


@odoo.tests.tagged("odx_owl", "post_install", "-at_install")
class OdxOwlHootSuite(odoo.tests.HttpCase):
    def test_odx_owl_components_desktop(self):
        env_filters = os.environ.get("ODX_OWL_HOOT_FILTERS", "").strip()
        if env_filters:
            hoot_filters = _get_parametric_hoot_filters([("+", env_filters)])
        else:
            hoot_filters = _get_parametric_hoot_filters(getattr(self, "_test_params", []))
        if not hoot_filters:
            hoot_filters = "".join(f"&id={_generate_hash(path)}" for path in SUITE_PATHS)
        self.browser_js(
            f"/web/tests?headless&loglevel=2&preset=desktop&timeout=15000{hoot_filters}",
            "",
            "",
            login="admin",
            timeout=3000,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )
