
How to use the need action mechanism in my addon
=================================================

Make your module inheriting from ir.needaction_mixin class

Feature integration
++++++++++++++++++++

::

  class my_module(osv.osv):
    _name = "my.module"
    _description = "My Module"
    _inherit = ['ir.needaction_mixin']
