import base64
import os
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Post-migration script to update main company branding to Harvard University
    and apply the module logo.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company", raise_if_not_found=False)
    if not company:
        company = env["res.company"].browse(1).exists()
    if company:
        vals = {"name": "Harvard University"}
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "static", "src", "img", "university_logo.png"
        )
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                vals["logo"] = base64.b64encode(f.read())
        company.write(vals)
