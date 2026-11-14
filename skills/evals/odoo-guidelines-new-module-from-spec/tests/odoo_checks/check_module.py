# Run by test.sh through `odoo-bin shell` on the database where the agent's
# module(s) were installed with demo data (env is the shell's environment).
# EVAL_MODULES lists the new modules, comma-separated. The checks need no name
# from the spec: they load what the modules declare. Each check prints one
# EVAL_RESULT line: {"check": ..., "ok": [...], "failed": [...]}.
import json
import os
import re
import traceback
from pathlib import Path

from lxml import etree

from odoo.modules.module import get_module_path
from odoo.tools.safe_eval import safe_eval

MODULES = [m for m in os.environ.get('EVAL_MODULES', '').split(',') if m]


def report(check, ok, failed, **extra):
    print('EVAL_RESULT ' + json.dumps({'check': check, 'ok': ok, 'failed': failed, **extra}))


def error_text(e):
    return f'{type(e).__name__}: {e}'.strip()[:500]


def declared(model):
    """Records of `model` the new modules declare in their data files."""
    imd = env['ir.model.data'].search([('module', 'in', MODULES), ('model', '=', model)])
    return [(f'{d.module}.{d.name}', env[model].browse(d.res_id).exists()) for d in imd]


def savepoint_check(name, func):
    try:
        with env.cr.savepoint():
            func()
        return None
    except Exception as e:  # noqa: BLE001 - reported
        return error_text(e)


# installed: every new module ends up installed.
states = {m.name: m.state for m in env['ir.module.module'].search([('name', 'in', MODULES)])}
report('installed', [m for m in MODULES if states.get(m) == 'installed'],
       [f'{m}: {states.get(m, "not found")}' for m in MODULES if states.get(m) != 'installed'])

# views: every view loads, inherited ones through the view they extend.
ok, failed = [], []
for xmlid, view in declared('ir.ui.view'):
    if not view:
        continue
    if view.type == 'qweb':
        err = savepoint_check(xmlid, lambda v=view: env['ir.qweb']._get_template(v.id))
    else:
        root = view
        while root.inherit_id:
            root = root.inherit_id
        err = savepoint_check(xmlid, lambda r=root: env[r.model].get_views([(r.id, r.type)]))
    (failed.append(f'{xmlid}: {err}') if err else ok.append(xmlid))
report('views', ok, failed)

# actions: window actions open (their views load, their domain evaluates and
# searches), menus load and point to existing actions.
ok, failed = [], []
eval_context = {'uid': env.uid, 'context': {}, 'allowed_company_ids': env.companies.ids, 'active_id': False, 'active_ids': []}
for xmlid, action in declared('ir.actions.act_window'):
    if not action:
        continue

    def open_action(a=action):
        Model = env[a.res_model]
        views = [(v.view_id.id, v.view_mode) for v in a.view_ids] or \
            [(a.view_id.id if a.view_id.type == mode else False, mode) for mode in a.view_mode.split(',')]
        Model.get_views(views + [(a.search_view_id.id, 'search')])
        Model.search_count(safe_eval(a.domain or '[]', eval_context))
    err = savepoint_check(xmlid, open_action)
    (failed.append(f'{xmlid}: {err}') if err else ok.append(xmlid))
for xmlid, menu in declared('ir.ui.menu'):
    if menu and menu.action and not menu.action.exists():
        failed.append(f'{xmlid}: its action does not exist')
    elif menu:
        ok.append(xmlid)
err = savepoint_check('load_menus', lambda: env['ir.ui.menu'].load_menus(False))
if err:
    failed.append(f'menus: {err}')
report('actions', ok, failed)

# static: the modules' Owl templates and other static XML parse, and the
# backend assets (their JS and SCSS) build without error.
ok, failed = [], []
for module in MODULES:
    module_path = get_module_path(module)
    if not module_path or not Path(module_path, 'static').exists():
        continue
    for xml in Path(module_path, 'static').rglob('*.xml'):
        if '/static/lib/' in str(xml):
            continue
        try:
            etree.parse(str(xml))
            ok.append(str(xml.relative_to(module_path)))
        except etree.XMLSyntaxError as e:
            failed.append(f'{module}/{xml.relative_to(module_path)}: {e}')
for bundle_name in ('web.assets_backend',):
    def build(name=bundle_name):
        bundle = env['ir.qweb']._get_asset_bundle(name)
        bundle.js()
        bundle.css()
        if bundle.css_errors:
            raise ValueError('; '.join(bundle.css_errors)[:500])
    err = savepoint_check(bundle_name, build)
    (failed.append(f'{bundle_name}: {err}') if err else ok.append(bundle_name))
report('static', ok, failed)

# crons: the scheduled actions the modules declare run without error, last
# because a cron may commit.
ok, failed = [], []
crons = [(xmlid, cron) for xmlid, cron in declared('ir.cron') if cron]
for xmlid, cron in crons:
    try:
        # A failing job does not raise: it is logged, and the error comes back
        # as a client action to display.
        result = cron.method_direct_trigger()
        env.cr.commit()
        if isinstance(result, dict) and result.get('type') == 'ir.actions.client':
            debug = ((result.get('params') or {}).get('data') or {}).get('debug') or json.dumps(result)
            # the cause comes first in the chained traceback, the RuntimeError
            # wrapping it last
            causes = [line for line in debug.splitlines()
                      if re.match(r'^[\w.]+(Error|Exception)\b', line) and not line.startswith('RuntimeError')]
            cause = (causes[0] if causes else debug.splitlines()[-1])[:500]
            failed.append(f'{xmlid}: the job failed: {cause}')
        else:
            ok.append(xmlid)
    except Exception as e:  # noqa: BLE001 - reported
        env.cr.rollback()
        failed.append(f'{xmlid}: {error_text(e)}')
        traceback.print_exc()
report('crons', ok, failed, count=len(crons))
env.cr.commit()
