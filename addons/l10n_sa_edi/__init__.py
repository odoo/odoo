from . import controllers
from . import demo
from . import models
from . import wizard


def _post_init_hook(env):
    """ Make Saudi companies use round globally """
    if sa_companies := env['res.company'].search([('chart_template', '=', 'sa')], order="parent_path"):
        for company in sa_companies:
            company.tax_calculation_rounding_method = 'round_globally'
