# Part of Odoo. See LICENSE file for full copyright and licensing details.
import fnmatch
import logging
import optparse
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
import odoo

from . import Command
_logger = logging.getLogger(__name__)


class Populate(Command):
    """ Inject fake data inside a database for testing """

    def run(self, cmdargs):
        parser = odoo.tools.config.parser
        parser.prog = f'{Path(sys.argv[0]).name} {self.name}'
        group = optparse.OptionGroup(parser, "Populate Configuration")
        group.add_option("--size", dest="population_size",
                        help="Populate database with auto-generated data. Value should be the population size: small, medium or large",
                        default='small')
        group.add_option("--models",
                         dest='populate_models',
                         help="Comma separated list of model or pattern (fnmatch)")
        group.add_option("--profile",
                         dest='profiling_enabled', action="store_true",
                         help="Specify if you want to profile records population.",
                         default=False)
        group.add_option("--rollback",
                         dest='populate_rollback', action="store_true",
                         help="Specify if you want to rollback database population.",
                         default=False)
        parser.add_option_group(group)
        opt = odoo.tools.config.parse_config(cmdargs)
        populate_models = opt.populate_models and set(opt.populate_models.split(','))
        dbname = odoo.tools.config['db_name']
        registry = odoo.registry(dbname)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            self.populate(
                env, opt.population_size, populate_models,
                profiling_enabled=opt.profiling_enabled,
                commit=not opt.populate_rollback)

    @classmethod
    def populate(cls, env, size, model_patterns=False, profiling_enabled=False, commit=True):
        registry = env.registry
        populated_models = None
        try:
            registry.populated_models = {}  # todo master, initialize with already populated models
            ordered_models = cls._get_ordered_models(env, model_patterns)

            _logger.log(25, 'Populating database')
            for model in ordered_models:
                if profiling_enabled:
                    profiling_context = odoo.tools.profiler.Profiler(
                        description=f'{model} {size}',
                        db=env.cr.dbname
                    )
                else:
                    profiling_context = nullcontext()

                if commit:
                    commit_context = nullcontext()
                else:
                    commit_context = patch('odoo.sql_db.Cursor.commit')

                _logger.info('Populating database for model %s', model._name)
                t0 = time.time()

                with profiling_context, commit_context:
                    registry.populated_models[model._name] = model._populate(size).ids

                    if not registry.populated_models[model._name]:
                        # Do not create ir.profile records
                        # for models without any population factories
                        profiling_context.db = False

                    # force the flush to make sure population time still
                    # considers flushing all values to database
                    env.flush_all()

                if commit:
                    env.cr.commit()

                model_time = time.time() - t0
                if model_time > 1:
                    _logger.info('Populated database for model %s (total: %fs) (average: %fms per record)',
                                 model._name, model_time, model_time / len(registry.populated_models[model._name]) * 1000)
        except:
            _logger.exception('Something went wrong populating database')
        finally:
            if not commit:
                env.cr.rollback()
            populated_models = registry.populated_models
            del registry.populated_models

        return populated_models

    @classmethod
    def _get_ordered_models(cls, env, model_patterns=False):
        _logger.info('Computing model order')
        processed = set()
        ordered_models = []
        visited = set()
        def add_model(model):
            if model not in processed:
                if model in visited:
                    raise ValueError('Cyclic dependency detected for %s' % model)
                visited.add(model)
                for dep in model._populate_dependencies:
                    add_model(env[dep])
                ordered_models.append(model)
                processed.add(model)
        for model in env.values():
            if model_patterns and not any(fnmatch.fnmatch(model._name, match) for match in model_patterns):
                continue
            if model._transient or model._abstract:
                continue
            ir_model = env['ir.model'].search([('model', '=', model._name)])
            if not model_patterns and all(module.startswith('test_') for module in ir_model.modules.split(',')):
                continue
            add_model(model)

        return ordered_models
