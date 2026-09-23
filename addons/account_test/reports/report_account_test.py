from odoo import api, models
from odoo.tools.safe_eval import datetime as safe_datetime
from odoo.tools.safe_eval import safe_eval

#
# Use period and Journal for selection or resources
#


class ReportAccount_TestReport_Accounttest(models.AbstractModel):
    _name = "report.account_test.report_accounttest"
    _description = "Account Test Report"

    @api.model
    def _execute_code(self, code_exec):
        def reconciled_inv():
            """
            returns the list of invoices that are set as reconciled = True
            """
            return self.env["account.move"].search([("reconciled", "=", True)]).ids

        def order_columns(item, cols=None):
            """
            This function is used to display a dictionary as a string, with its columns in the order chosen.

            :param item: dict
            :param cols: list of field names
            :returns: a list of tuples (fieldname: value) in a similar way that would dict.items() do except that the
                returned values are following the order given by cols
            :rtype: [(key, value)]
            """
            if cols is None:
                cols = list(item)
            return [(col, item.get(col)) for col in cols if col in item]

        context = {
            "cr": self.env.cr,
            "uid": self.env.uid,
            "reconciled_inv": reconciled_inv,  # specific function used in different tests
            "result": None,  # used to store the result of the test
            "column_order": None,  # used to choose the display order of columns (in case you are returning a list of dict)
            "_": self.env._,  # pylint: disable=E8502,
        }
        safe_eval(code_exec, context, mode="exec")
        result = context["result"]
        column_order = context.get("column_order")

        if not isinstance(result, (tuple, list, set)):
            result = [result]
        if not result:
            result = [self.env._("The test was passed successfully")]
        else:

            def _format(item):
                if isinstance(item, dict):
                    return ", ".join(
                        [
                            "%s: %s" % (tup[0], tup[1])
                            for tup in order_columns(item, column_order)
                        ]
                    )
                else:
                    return item

            result = [_format(rec) for rec in result]

        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        # `self` is an AbstractModel here, so `self.ids` is always empty: the
        # records to print are the ones the caller passed. And the raw datetime
        # module is refused by `safe_eval.check_values`, which every qweb render
        # runs -- the wrapped one is what a template may hold.
        return {
            "doc_ids": docids,
            "doc_model": "accounting.assert.test",
            "docs": self.env["accounting.assert.test"].browse(docids),
            "data": data,
            "execute_code": self._execute_code,
            "datetime": safe_datetime,
        }
