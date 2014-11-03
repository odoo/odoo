============================
odoo developer documentation
============================

Welcome to the Odoo developer documentation.

This documentation is incomplete and may contain errors, if you wish to
contribute, every page should have a :guilabel:`View on Github` link:

.. image:: images/view-on-github.*
    :align: center

Through this link you can edit documents and submit changes for review using
`github's web interface
<https://help.github.com/articles/editing-files-in-your-repository/>`_.
Contributions are welcome and appreciated.

.. todo:: what's the documentation's license?

The documentation is currently organized in four sections:

* :doc:`tutorials`, aimed at introducing the primary areas of developing Odoo
  modules
* :doc:`reference`, which ought be the complete and canonical documentation
  for Odoo subsystems
* :doc:`modules`, documenting useful specialized modules and integration
  methods (and currently empty)

.. hidden toctree w/o titlesonly otherwise the titlesonly "sticks" to
   in-document toctrees and we can't have a toctree showing both "sibling"
   pages and current document sections

.. toctree::
    :hidden:

    tutorials
    reference
    modules

.. ifconfig:: todo_include_todos

    .. rubric:: Things to add and fix

    .. todolist::
