:orphan:

Using the Odoo theme
====================

* copy the theme to one of your theme paths
* in your ``conf.py``,

    - add the package as the ``html_theme`` in your ``conf.py``::

        html_theme = 'odoodoc'

    - add the theme path to ``sys.path`` in your ``conf.py``::

        sys.path.insert(0, os.path.abspath('./_themes'))

    - add the theme as an extension::

        extensions = ['odoodoc']

Custom styling
--------------

If you need to add custom/own styles, add a CSS to your static files, set it
as ``html_style`` in your ``conf.py`` and add the following as its first
line::

    @import url(odoodoc.css)
