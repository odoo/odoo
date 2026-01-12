# register protocols first
from . import odoo_file_system
from . import rooted_dir_file_system

# then add normal imports
from . import models
from . import wizards
