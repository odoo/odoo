import json

from odoo import http
from odoo.addons.web.controllers.export import CSVExport, ExcelExport


def adapt_analytic_distribution_into_analytic_lines_data(data):

    def get_analytic_fields_to_add():
        project_plan, other_plans = http.request.env['account.analytic.plan']._get_all_plans()
        return (
            [{'name': 'analytic_line_ids/amount', 'label': 'Analytic Amount'}]
            + [{'name': 'analytic_line_ids/account_id', 'label': project_plan.name}]
            + [{'name': f'analytic_line_ids/{plan_field.name}', 'label': plan_field.field_description} for plan_field in other_plans._find_plan_column()]
        )

    data_dic = json.loads(data)
    if data_dic.get('model') != 'account.move.line':
        return data

    fields_data_lst = data_dic['fields']
    for i, field_data_dic in enumerate(fields_data_lst):
        if field_data_dic['name'] == 'analytic_distribution':
            data_dic['fields'] = fields_data_lst[:i] + get_analytic_fields_to_add() + fields_data_lst[i + 1:]
            return json.dumps(data_dic)

    return data


class CSVExportAccountMoveLine(CSVExport):

    def base(self, data):
        data = adapt_analytic_distribution_into_analytic_lines_data(data)
        return super().base(data)


class ExcelExportAccountMoveLine(ExcelExport):

    def base(self, data):
        data = adapt_analytic_distribution_into_analytic_lines_data(data)
        return super().base(data)
