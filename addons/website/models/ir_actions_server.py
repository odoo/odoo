from odoo import api, fields, models
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.web import urls
from odoo.tools.json import scriptsafe as json_scriptsafe

_debug = DebugLog(__name__)


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    xml_id = fields.Char(
        string="External ID",
        compute="_compute_xml_id",
        help="ID of the action if defined in a XML file",
    )
    website_path = fields.Char()
    website_url = fields.Char(
        compute="_compute_website_url",
        help="The full URL to access the server action through the website.",
    )
    website_published = fields.Boolean(
        string="Available on the Website",
        copy=False,
        help="A code server action can be executed from the website, using a dedicated "
        "controller. The address is <base>/website/action/<website_path>. "
        "Set this field as True to allow users to run this action. If it "
        "is set to False the action cannot be run through the website.",
    )

    def _compute_xml_id(self):
        res = self.get_external_id()
        for action in self:
            action.xml_id = res.get(action.id)

    @api.depends("state", "website_published", "website_path", "xml_id")
    def _compute_website_url(self):
        for action in self:
            if action.state == "code" and action.website_published:
                action.website_url = action._get_website_url(
                    action.website_path, action.xml_id
                )
            else:
                action.website_url = False

    def _get_website_url(self, website_path, xml_id):
        base_url = self.get_base_url()
        link = website_path or xml_id or (self.id and "%d" % self.id) or ""
        if base_url and link:
            path = "%s/%s" % ("/website/action", link)
            return urls.urljoin(base_url, path)
        return ""

    @api.model
    def _prepare_eval_context(self, action):
        eval_context = super()._prepare_eval_context(action)
        if action and action.state == "code":
            eval_context["request"] = request
            eval_context["json"] = json_scriptsafe
        return eval_context

    @api.model
    def _run_action_code_multi(self, eval_context=None):
        res = super()._run_action_code_multi(eval_context)
        _debug.logic(
            "server_action_response",
            by="eval_context" if "response" in eval_context else "super",
        )
        return eval_context.get("response", res)
