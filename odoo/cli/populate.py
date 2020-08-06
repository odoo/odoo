#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import fnmatch
import logging
import odoo

_logger = logging.getLogger(__name__)


def main():
    with odoo.api.Environment.manage():
        dbname = odoo.config['db_name']
        registry = odoo.registry(dbname)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            populate(env, odoo.config['population_size'], odoo.config['populate_models'])


def populate(env, size, model_patterns=False):
    registry = env.registry
    populated_models = None
    try:
        registry.populated_models = {}  # todo master, initialize with already populated models
        ordered_models = _get_ordered_models(env, model_patterns)

        _logger.log(25, 'Populating database')
        for model in ordered_models:
            _logger.info('Populating database for model %s', model._name)
            t0 = time.time()
            registry.populated_models[model._name] = model._populate(size).ids
            # todo indicate somewhere that model is populated
            env.cr.commit()
            model_time = time.time() - t0
            if model_time > 1:
                _logger.info('Populated database for model %s in %ss', model._name, model_time)
    except:
        _logger.exception('Something went wrong populating database')
    finally:
        populated_models = registry.populated_models
        del registry.populated_models

    return populated_models


def _get_ordered_models(env, model_patterns=False):
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
        ir_model = env['ir.model'].search([('model', '=', model._name)])
        if model_patterns and not any(fnmatch.fnmatch(model._name, match) for match in model_patterns):
            continue
        if model._transient or model._abstract:
            continue
        if not model_patterns and all(module.startswith('test_') for module in ir_model.modules.split(',')):
            continue
        add_model(model)

    return ordered_models
