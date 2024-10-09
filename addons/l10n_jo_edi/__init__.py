from . import models


def _post_init_hook(env):
    """ Make Jordan companies use round globally """
    if jo_companies := env['res.company'].search([('chart_template', '=', 'jo_standard')], order="parent_path"):
        for company in jo_companies:
            company.tax_calculation_rounding_method = 'round_globally'
