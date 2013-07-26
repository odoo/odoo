.. _ir-actions:

Ir Actions
===========

.. _ir-actions-server:

Server actions
++++++++++++++

.. versionchanged:: 8.0

.. currentmodule:: openerp.addons.base.ir.ir_actions

.. autoclass:: actions_server
  :noindex:

Adding a new sever action
-------------------------

The ``state`` field holds the various available types of server action. In order
to add a new server action, the first thing to do is to override the ``_get_states``
method that returns the list of values available for the selection field.

.. automethod:: actions_server._get_states
  :noindex:

The method called when executing the server action is the ``run`` method. This
method calls ``run_action_<STATE>``. When adding a new server action type, you
have to define the related method that will be called upon execution.

.. automethod:: actions_server.run
  :noindex:

Changelog
---------

`8.0`
'''''

The refactoring of OpenERP 8.0 server actions removed the following types of
server action:

 - ``loop``: can be replaced by a ``code`` action
 - ``dummy``: can be replaced by a void ``code`` action
 - ``object_create`` and ``object_copy`` have been merged into a single and
   more understandable ``object_create`` action
 - ``other`` is renamed ``multi`` and raises in case of loops
