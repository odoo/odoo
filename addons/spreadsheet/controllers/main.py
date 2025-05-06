import logging


from odoo import http
from odoo.http import request, Controller

logger = logging.getLogger(__name__)


class SpreadsheetController(Controller):

    @http.route("/spreadsheet/log", type="json", auth="user", methods=["POST"])
    def log_action(self, type, datasources, **kw):
        if datasources:
            self._log(type, request.env.uid, datasources)

    def _log(self, type, user_id, datasources):
        if type not in ["download", "copy", "print"]:
            return
        data = [src for src in (self._stringify_source(datasource) for datasource in datasources) if src]
        if not data:
            return
        logger.info(
            "User %d exported (%s) spreadsheet data (%s) from %s",
            user_id, type, "), (".join(data), request.httprequest.environ["REMOTE_ADDR"]
        )

    @classmethod
    def _stringify_source(self, source):
        res_model = source.get("resModel")
        if not res_model or res_model not in request.env:
            return

        model = request.env[res_model]
        fields = source.get("fields", [])
        if not fields:
            return

        string = f"model: {res_model} fields: [{','.join(fields)}]"

        groupby = source.get("groupby")
        if groupby:
            groupby = [field.split(":")[0] for field in source.get("fields", []) if field.split(":")[0] in model._fields]
            string += f" grouped by [{','.join(groupby)}]"
        
        domain = source.get("domain")
        if domain:
            string += f" with domain {domain}"

        return string
