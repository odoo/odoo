from odoo.addons.mail.tools.js_model_generation import MODELS_TO_EXPOSE, MODELS_TO_INCLUDE

MODELS_TO_EXPOSE.extend(["hr.employee", "hr.department"])
MODELS_TO_INCLUDE.extend(["hr.employee", "hr.department"])
