from odoo.tools.module_data import adopt_xmlids

SPECIFICATIONS = (
    "fuel_tank_capacity",
    "fuel_efficiency_theoretical",
    "fuel_efficiency_min",
    "fuel_efficiency_max",
    "fuel_efficiency_uom_name",
)
# `product.product` delegates to `product.template`, so each specification is
# reflected there under its own xmlid and has to move with the original.
MOVED_FIELDS = [
    f"field_product_{model}__{name}"
    for model in ("template", "product")
    for name in SPECIFICATIONS
] + ["field_resource_asset__fuel_tank_capacity"]


def migrate(cr, version):
    # A tank and a consumption rate are specifications of a vehicle model, so
    # they are declared here now. Adopting them before either module loads is
    # what keeps `product_asset` from leaving an orphaned xmlid behind.
    adopt_xmlids(cr, "product_asset", "fleet", MOVED_FIELDS)
