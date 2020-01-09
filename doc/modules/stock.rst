:orphan:

.. sphinx autodoc information : https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

.. _modules/stock:

=========
Inventory
=========




Products
========

.. currentmodule:: addons.stock.models.product

.. autoclass:: Product()
    :members:

.. autoclass:: ProductTemplate()
    :members:

Warehouse
=========

.. currentmodule:: addons.stock.models.stock_warehouse

.. autoclass:: Warehouse()
    :members:

Location
========

.. currentmodule:: addons.stock.models.stock_location

.. autoclass:: Location()
    :members:

Quant
-----

.. currentmodule:: addons.stock.models.stock_quant

.. autoclass:: StockQuant()
    :members: _get_removal_strategy, _get_available_quantity, _gather

.. VFE NOTE (not rendered):

    LIST :members: methods to document
        (if empty, all documented public methods due to Odoo default Doc configuration)
    FLAG :undoc-members: to document undocumented members
    FLAG :private-members: to document undocumented members (no impact if specific members are specified)

Moves
=====

.. currentmodule:: addons.stock.models.stock_move

.. autoclass:: StockMove()
    :members:

Lines
-----

.. currentmodule:: addons.stock.models.stock_move_line

.. autoclass:: StockMoveLine()
    :members: