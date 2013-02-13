.. _orm-methods:

ORM methods
===========

.. _orm-workflows:

Workflow-related methods
------------------------

.. versionadded:: 7.1

Creating, deleting, or otherwise manipulating workflow instances is possible
right from a Model instance. (Previously, workflows were handled throught a
call to ``LocalService('workflow')``. Using the ORM methods is now the preferred
way.)

.. currentmodule:: openerp.osv.orm

.. automethod:: BaseModel.create_workflow
  :noindex:

  This is used instead of ``LocalService('workflow').trg_create()``.

.. automethod:: BaseModel.delete_workflow
  :noindex:

  This is used instead of ``LocalService('workflow').trg_delete()``.

.. automethod:: BaseModel.step_workflow
  :noindex:

  This is used instead of ``LocalService('workflow').trg_write()``.

.. automethod:: BaseModel.redirect_workflow
  :noindex:

.. automethod:: BaseModel.signal_workflow
  :noindex:

  This is used instead of ``LocalService('workflow').trg_validate()``.

.. method:: BaseModel.signal_xxx(cr, uid, ids)
  :noindex:

  Sends a signal ``xxx`` to the workflow instances bound to the given record
  IDs. (This is implemented using ``__getattr__`` so no source link is
  rendered on the right.)

  This is used instead of ``LocalService('workflow').trg_validate()``.


.. note::
  Low-level access to the workflows is still possible by using the
  ``openerp.workflow`` module, that is, in a similar way to what was possible
  with the previous ``LocalService('workflow')`` access. This may be useful
  when looking-up a model in the registry and/or its records is not necessary.
  For instance when working with raw model names and record IDs is preferred (to
  avoid hitting unnecessarily the database). But this is something that should be
  carefully considered as it would bypass the ORM methods (and thus any inherited
  behaviors).
