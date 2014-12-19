import inspect
import importlib
import os.path
from urlparse import urlunsplit

def setup(app):
    app.add_config_value('github_user', None, 'env')
    app.add_config_value('github_project', None, 'env')
    app.connect('html-page-context', add_doc_link)

    def linkcode_resolve(domain, info):
        """ Resolves provided object to corresponding github URL
        """
        # TODO: js?
        if domain != 'py':
            return None
        if not (app.config.github_user and app.config.github_project):
            return None

        module, fullname = info['module'], info['fullname']
        # TODO: attributes/properties don't have modules, maybe try to look
        #       them up based on their cached host object?
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
            app,
            os.path.relpath(obj_source_path, project_root),
            line)
    app.config.linkcode_resolve = linkcode_resolve

def make_github_link(app, path, line=None, mode="blob"):
    config = app.config

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

def add_doc_link(app, pagename, templatename, context, doctree):
    """ Add github_link function linking to the current page on github """
    if not app.config.github_user and app.config.github_project:
        return

    # can't use functools.partial because 3rd positional is line not mode
    context['github_link'] = lambda mode='mode': make_github_link(
        app, 'doc/%s%s' % (pagename, app.config.source_suffix), mode=mode)
