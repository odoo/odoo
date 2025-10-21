import logging
import optparse
import sys
import time

from odoo import api
from odoo.modules.registry import Registry
from odoo.tools import config
from odoo.tools.populate import populate_models

from . import Command

DEFAULT_FACTOR = '10000'
DEFAULT_SEPARATOR = '_'
DEFAULT_MODELS = 'res.partner,product.template,account.move,sale.order,crm.lead,stock.picking,project.task'

_logger = logging.getLogger(__name__)


class Populate(Command):
    """Populate database via duplication of existing data for testing/demo purposes"""

    def run(self, cmdargs):
        parser = config.parser
        parser.prog = self.prog
        group = optparse.OptionGroup(parser, "Populate Configuration")
        group.add_option("--factors", dest="factors",
                         help="Comma separated list of factors for each model, or just a single factor."
                              "(Ex: a factor of 3 means the given model will be copied 3 times, reaching 4x it's original size)"
                              "The last factor is propagated to the remaining models without a factor.",
                         default=DEFAULT_FACTOR)
        group.add_option("--models",
                         dest='models_to_populate',
                         help="Comma separated list of models",
                         default=DEFAULT_MODELS)
        group.add_option("--sep",
                         dest='separator',
                         help="Single character separator for char/text fields.",
                         default=DEFAULT_SEPARATOR)
        parser.add_option_group(group)
        opt = config.parse_config(cmdargs + ['--no-http'], setup_logging=True)

        # deduplicate models if necessary, and keep the last corresponding
        # factor for each model
        opt_factors = [int(f) for f in opt.factors.split(',')]
        model_factors = {
            model_name: opt_factors[index] if index < len(opt_factors) else opt_factors[-1]
            for index, model_name in enumerate(opt.models_to_populate.split(','))
        }
        try:
            separator_code = ord(opt.separator)
        except TypeError:
            raise ValueError("Separator must be a single Unicode character.")

        dbnames = config['db_name']
        if len(dbnames) > 1:
            sys.exit("-d/--database/db_name has multiple database, please provide a single one")
        registry = Registry(dbnames[0])
        with registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {'active_test': False})
            self.populate(env, model_factors, separator_code)

    @classmethod
    def populate(cls, env: api.Environment, modelname_factors: dict[str, int], separator_code: int):
        model_factors = {
            model: factor
            for model_name, factor in modelname_factors.items()
            if (model := env.get(model_name)) is not None and not (model._transient or model._abstract)
        }
        _logger.log(25, 'Populating models %s', list(model_factors))
        t0 = time.time()
        populate_models(model_factors, separator_code)
        env.flush_all()
        model_time = time.time() - t0
        _logger.info('Populated models %s (total: %fs)', list(model_factors), model_time)
