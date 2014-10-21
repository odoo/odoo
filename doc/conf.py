# -*- coding: utf-8 -*-
import sys, os
import sphinx

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
DIR = os.path.dirname(__file__)
sys.path.append(
    os.path.abspath(
        os.path.join(DIR, '_themes')))
# autodoc
sys.path.append(os.path.abspath(os.path.join(DIR, '..')))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.1'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.ifconfig',
    'sphinx.ext.todo',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'odoodoc',
    'patchqueue'
]
if sphinx.__version__.split('.') >= ['1', '2']:
    # linkcode is only available from Sphinx 1.2
    extensions.insert(0, 'sphinx.ext.linkcode')


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'odoo'
copyright = u'2014, OpenERP s.a.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'master'
# The full version, including alpha/beta/rc tags.
release = 'master'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'odoo'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'odoodoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_style = "odoo.css"

html_add_permalinks = False

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# FIXME: no sidebar on index?
html_sidebars = {
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# default must be set otherwise ifconfig blows up
todo_include_todos = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/2/', None),
    'werkzeug': ('http://werkzeug.pocoo.org/docs/', None),
    'sqlalchemy': ('http://docs.sqlalchemy.org/en/rel_0_9/', None),
    'django': ('https://django.readthedocs.org/en/latest/', None),
}

github_user = 'odoo'
github_project = 'odoo'

def setup(app):
    app.connect('html-page-context', canonicalize)
    app.add_config_value('canonical_root', None, 'env')
    app.add_config_value('canonical_branch', 'master', 'env')

    app.connect('html-page-context', versionize)
    app.add_config_value('versions', '', 'env')

def canonicalize(app, pagename, templatename, context, doctree):
    """ Adds a 'canonical' URL for the current document in the rendering
    context. Requires the ``canonical_root`` setting being set. The canonical
    branch is ``master`` but can be overridden using ``canonical_branch``.
    """
    if not app.config.canonical_root:
        return

    context['canonical'] = _build_url(
        app.config.canonical_root, app.config.canonical_branch, pagename)

def versionize(app, pagename, templatename, context, doctree):
    """ Adds a version switcher below the menu, requires ``canonical_root``
    and ``versions`` (an ordered, space-separated lists of all possible
    versions).
    """
    if not (app.config.canonical_root and app.config.versions):
        return

    context['versions'] = [
        (vs, _build_url(app.config.canonical_root, vs, pagename))
        for vs in app.config.versions.split(',')
        if vs != app.config.version
    ]

def _build_url(root, branch, pagename):
    return "{canonical_url}{canonical_branch}/{canonical_page}".format(
        canonical_url=root,
        canonical_branch=branch,
        canonical_page=(pagename + '.html').replace('index.html', '')
                                           .replace('index/', ''),
    )

