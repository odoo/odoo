import logging
import time

from odoo import api  # noqa: TC001 — runtime import required (PEP 649)
from odoo.tools import config
from odoo.tools.populate import populate_models

from . import Command, get_single_database, odoo_env
from .command import build_config_args

DEFAULT_FACTOR = (
    "10000"  # NOTE: string intentional — argparse delivers user input as str
)
DEFAULT_SEPARATOR = "_"
DEFAULT_MODELS = "res.partner,product.template,account.move,sale.order,crm.lead,stock.picking,project.task"

_logger = logging.getLogger(__name__)


class Populate(Command):
    """Populate database via duplication of existing data for testing/demo purposes"""

    def run(self, cmdargs):
        parser = self.parser
        self.add_config_arguments(parser)
        parser.add_argument(
            "--factors",
            dest="factors",
            help="Comma separated list of factors for each model, or just a single factor."
            "(Ex: a factor of 3 means the given model will be copied 3 times, reaching 4x it's original size)"
            "The last factor is propagated to the remaining models without a factor.",
            default=DEFAULT_FACTOR,
        )
        parser.add_argument(
            "--models",
            dest="models_to_populate",
            help="Comma separated list of models",
            default=DEFAULT_MODELS,
        )
        parser.add_argument(
            "--sep",
            dest="separator",
            help="Single character separator for char/text fields.",
            default=DEFAULT_SEPARATOR,
        )
        parsed_args = parser.parse_args(cmdargs)

        config_args = build_config_args(
            parsed_args.config, parsed_args.db_name, extra_args=["--no-http"]
        )
        config.parse_config(config_args, setup_logging=True)

        # deduplicate models if necessary, and keep the last corresponding
        # factor for each model
        opt_factors = [int(f) for f in parsed_args.factors.split(",")]
        model_factors = {
            model_name: (
                opt_factors[index] if index < len(opt_factors) else opt_factors[-1]
            )
            for index, model_name in enumerate(
                parsed_args.models_to_populate.split(",")
            )
        }
        try:
            separator_code = ord(parsed_args.separator)
        except TypeError:
            msg = "Separator must be a single Unicode character."
            raise ValueError(msg)

        db_name = get_single_database(config["db_name"])
        with odoo_env(db_name, context={"active_test": False}) as env:
            self.populate(env, model_factors, separator_code)

    @classmethod
    def populate(
        cls,
        env: api.Environment,
        modelname_factors: dict[str, int],
        separator_code: int,
    ):
        """Populate models with synthetic data."""
        model_factors = {
            model: factor
            for model_name, factor in modelname_factors.items()
            if (model := env.get(model_name)) is not None
            and not (model._transient or model._abstract)
        }
        _logger.log(logging.RUNBOT, "Populating models %s", list(model_factors))
        t0 = time.time()
        populate_models(model_factors, separator_code)
        env.flush_all()
        model_time = time.time() - t0
        _logger.info(
            "Populated models %s (total: %fs)", list(model_factors), model_time
        )
