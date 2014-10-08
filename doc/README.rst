:orphan:

==================
Odoo Documentation
==================

Odoo Theme
==========

The Odoo Documentation theme is a bootstrap-based mix of http://odoo.com and
http://getbootstrap.com with additional changes and additions, bundled as
a Sphinx theme.

The main style file is ``_themes/odoodoc/static/style.less``, it is not
converted on the fly and must be compiled manually when altere, using the
official node-based lessc_ tool.

``odoodoc`` must be added as an extension to a project using the theme, it
fixes some discrepancies between bootstrap_ and Sphinx_ and adds a few
features:

Sphinx Customizations
---------------------

* toctree bullet lists (HTML ``<ul>``) are given the ``nav`` class
* the main navigation bar also gets the ``navbar-nav`` and ``navbar-right``
  set on its root (``navbar-right`` could probably be handled in CSS to avoid
  having it in the markup)
* tables are given the ``table`` class
* colspecs are removed from tables, tables should autolayout
* ``data-`` attributes are copied straight from the docutils node to the
  output HTML node
* an ``odoo`` pygments style based on the bootstrap_ documentation's
* the normal Sphinx sidebars are suppressed and a new sidebar is injected in
  ``div.document`` (``sidebar1`` is outside in the base Sphinx layout)
* HTML5 doctype

Additional features
-------------------

* versions switcher, uses the ``canonical_root`` setting and an additional
  ``versions`` setting which should be a comma-separated list of available
  versions. Appends the each version and page name to the root, and displays
  a list of those links on the current page
* canonical urls, requires a ``canonical_root`` setting value, and optionally
  a ``canonical_branch`` (default: ``master``)
* :guilabel:`Edit on github` link in Sphinx pages if ``github_user`` and
  ``github_project`` are provided
* :guilabel:`[source]` links in autodoc content links to github with the same
  requirements (requires Sphinx 1.2)
* ``aphorism`` class for admonitions, makes the first line of the admonition
  inline and the same size as the admonition category (mostly for short,
  single-phrase admonitions)
* ``exercise`` directive, mostly for training-type documents, the
  ``solutions`` tag_ can be used to conditionally show e.g. solutions
* a number of straight-to-HTML directives:

  ``h:div``
    a straight div, can be used instead of ``container`` (which adds the
    ``container`` class to the div it generates, that's really not compatible
    with Bootstrap_)
  ``h:address``
    generates an ``<address>`` node
  a bunch of roles straight to HTML inline
    ``mark``, ``insert``, ``delete``, ``strikethrough``, ``small`, ``kbd`` and
    ``var`` generate the corresponding HTML element

Requirements
------------

* Sphinx 1.1, 1.2 for code Python code links
* sphinx-patchqueue (for the content, not the theme)

.. _lessc: http://lesscss.org/#using-less
.. _bootstrap: http://getbootstrap.com
.. _sphinx: http://sphinx-doc.org
.. _tag: http://sphinx-doc.org/markup/misc.html#including-content-based-on-tags
