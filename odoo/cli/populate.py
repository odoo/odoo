import argparse
import logging
import textwrap
import time

from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.registry import Registry
from odoo.tools import config
from odoo.tools.populate import populate_models

from . import Command

DEFAULT_FACTOR = '10000'
DEFAULT_SEPARATOR = '_'
DEFAULT_MODELS = ",".join([  # noqa: FLY002
    'account.move',
    'crm.lead',
    'product.template',
    'project.task',
    'res.partner',
    'sale.order',
    'stock.picking',
])

_logger = logging.getLogger(__name__)


class Populate(Command):
    """Populate database via duplication of existing data for testing/demo purposes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parser.formatter_class = argparse.RawTextHelpFormatter
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        self.parser.add_argument(
            "--models", dest='models_to_populate', metavar='MODEL,...', default=DEFAULT_MODELS,
            help=textwrap.dedent("""
                Comma separated list of models.
                Default models:
            """) + '\n'.join(f"    {model}" for model in DEFAULT_MODELS.split(',')))
        self.parser.add_argument(
            "--factors", default=DEFAULT_FACTOR,
             help=textwrap.dedent("""
                 Comma separated list of factors for each model.
                 Ex: a factor of 3 means the given model will be copied 3 times,
                 reaching 4 times its original size. The last factor is propagated
                 to the remaining models without a factor.
            """))
        self.parser.add_argument(
            "--sep", dest='separator', default=DEFAULT_SEPARATOR,
            help="Single character separator for char/text fields")
        self.parser.epilog = textwrap.dedent("""\

            Some models will also populate other dependent models.
            i.e.: the model `account.move` will also populate `account.move.lines`
        """)

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = []
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]

        config.parse_config(config_args, setup_logging=True)

        db_names = config['db_name']
        if not db_names or len(db_names) > 1:
            self.parser.error("Please provide a single database")
        parsed_args.db_name = db_names[0]

        try:
            separator_code = ord(parsed_args.separator)
        except TypeError:
            self.parser.error("Separator must be a single Unicode character.")

        # deduplicate models if necessary, and keep the last corresponding
        # factor for each model
        opt_factors = [int(f) for f in parsed_args.factors.split(',')]
        model_factors = {
            model_name: opt_factors[index] if index < len(opt_factors)
            else opt_factors[-1]
            for index, model_name in enumerate(parsed_args.models_to_populate.split(','))
        }

        with Registry(parsed_args.db_name).cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {'active_test': False})
            self.populate(env, model_factors, separator_code)

            model_factors = {
                model: factor
                for model_name, factor in model_factors.items()
                if (model := env.get(model_name)) is not None
                   and not (model._transient or model._abstract)
            }
            model_names = str(list(model_factors))
            _logger.log(25, 'Populating models %s', model_names)

            t0 = time.time()

            populate_models(model_factors, separator_code)
            env.flush_all()

            model_time = time.time() - t0
            _logger.info('Populated models %s (total: %fs)', model_names, model_time)
