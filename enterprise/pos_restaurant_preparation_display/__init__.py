from . import models
from odoo.tools import convert

def _pos_restaurant_preparation_display_post_init(env):
    env['pos.config']._load_preparation_display_data()
