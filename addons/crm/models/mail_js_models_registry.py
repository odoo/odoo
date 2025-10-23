from odoo.addons.mail.tools.mail_js_models_registry import MODELS_TO_EXPOSE, MODELS_TO_INCLUDE

MODELS_TO_EXPOSE.extend(["crm.lead"])
MODELS_TO_INCLUDE.extend(["crm.lead"])
