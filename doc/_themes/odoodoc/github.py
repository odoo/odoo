import inspect
import importlib
import os.path
from urlparse import urlunsplit

# FIXME: better way to handle this?
_app = None
def setup(app):
    global _app
    _app = app
    app.add_config_value('github_user', None, 'env')
    app.add_config_value('github_project', None, 'env')

def linkcode_resolve(domain, info):
    # TODO: js?
    if domain != 'py':
        return None

    module, fullname = info['module'], info['fullname']
    # TODO: attributes/properties don't have modules, maybe try to look them
    # up based on their cached host object?
    if not module:
        return None

    obj = importlib.import_module(module)
    for item in fullname.split('.'):
        obj = getattr(obj, item, None)

    if obj is None:
        return None

    # get original from decorated methods
    try: obj = getattr(obj, '_orig')
    except AttributeError: pass

    try:
        obj_source_path = inspect.getsourcefile(obj)
        _, line = inspect.getsourcelines(obj)
    except (TypeError, IOError):
        # obj doesn't have a module, or something
        return None

    import openerp
    project_root = os.path.join(os.path.dirname(openerp.__file__), '..')
    return make_github_link(
        os.path.relpath(obj_source_path, project_root),
        line)

def make_github_link(path, line=None, mode="blob"):
    config = _app.config
    if not (config.github_user and config.github_project):
        return None

    urlpath = "/{user}/{project}/{mode}/{branch}/{path}".format(
        user=config.github_user,
        project=config.github_project,
        branch=config.version or 'master',
        path=path,
        mode=mode,
    )
    return urlunsplit((
        'https',
        'github.com',
        urlpath,
        '',
        '' if line is None else 'L%d' % line
    ))

def github_doc_link(pagename, mode='blob'):
    return make_github_link(
        'doc/%s%s' % (pagename, _app.config.source_suffix), mode=mode)
