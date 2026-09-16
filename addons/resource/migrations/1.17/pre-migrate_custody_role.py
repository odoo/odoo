from odoo.tools import module_data


def migrate(cr, version):
    """`resource.assignment.role` is the custody role, and says so.

    `resource.role` is a different thing entirely -- a role a resource can fill,
    held as a many2many on the resource -- and two models one module apart both
    spelling it `role` is how redundancy hides. A reader seeing `.role` could not
    tell which of the two they had.

    Renamed in place rather than dropped and re-added, so the column keeps its data
    and the `ir.model.fields` row keeps its id: every tracking value, export
    template and access record points at that id.
    """
    module_data.rename_field(cr, "resource.assignment", "role", "custody_role")
