import logging


from odoo import http
from odoo.http import request, Controller

logger = logging.getLogger(__name__)


class SpreadsheetController(Controller):

    @http.route("/spreadsheet/log", type="jsonrpc", auth="user", methods=["POST"])
    def log_action(self, action_type, datasources, **kw):
        if datasources:
            self._log_spreadsheet_export(action_type, request.env.uid, datasources)

    def _log_spreadsheet_export(self, action_type, user_id, datasources):
        if action_type not in ["download", "copy", "freeze", "print"]:
            return
        data = [src for datasource in datasources if (src := self._stringify_source(datasource))]
        if not data:
            return
        logger.info(
            "User %d exported (%s) spreadsheet data (%s) from %s",
            user_id, action_type, "), (".join(data), request.httprequest.environ["REMOTE_ADDR"]
        )

    @staticmethod
    def _stringify_source(source):
        res_model = source.get("resModel")
        if not res_model or res_model not in request.env:
            return

        if not (fields := source.get("fields", [])):
            return

        string = f"model: {res_model} with fields: [{','.join(fields)}]"

        if groupby := source.get("groupby"):
            string += f" grouped by [{','.join(groupby)}]"

        if domain := source.get("domain"):
            string += f" with domain {domain}"

        return string
