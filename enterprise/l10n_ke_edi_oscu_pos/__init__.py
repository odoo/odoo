from . import models


def set_update_stock_real_time(env):
    for company in env['res.company'].search([('partner_id.country_id.code', '=', 'KE')]):
        company.point_of_sale_update_stock_quantities = 'real'
