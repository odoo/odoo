Need action mechanism
=====================

base.needaction mixin class
+++++++++++++++++++++++++++

This revision adds a mixin class for objects using the need action feature.

Need action feature can be used by objects willing to be able to signal that an action is required on a particular record. If in the business logic an action must be performed by somebody, for instance validation by a manager, this mechanism allows to set a list of users asked to perform an action.

This class wraps a table (base.needaction_users_rel) that behaves like a many2many field. However, no field is added to the model inheriting from base.needaction. The mixin class manages the low-level considerations of updating relationships. Every change made on the record calls a method that updates the relationships.

Objects using the need_action feature should override the ``get_needaction_user_ids`` method. This methods returns a dictionary whose keys are record ids, and values a list of user ids, like in a many2many relationship. Therefore by defining only one method, you can specify if an action is required by defining the users that have to do it, in every possible situation.

This class also offers several global services,:
 - ``needaction_get_record_ids``: for a given model_name and uid, get all record ids that ask this user to perform an action. This mechanism is used for instance to display the number of pending actions in menus, such as Leads (12)
 - ``needaction_get_action_count``: as ``needaction_get_record_ids`` but returns only the number of action, not the ids (performs a search with count=True)
 - ``needaction_get_user_record_references``: for a given uid, get all the records that ask this user to perform an action. Records are given as references, a list of tuples (model_name, record_id)

Menu modification
+++++++++++++++++

This revision adds two functional fields to ``ir.ui.menu`` model :
 - ``uses_needaction``: boolean field. If the menu entry is related to a act_window action, and this action is related to a model that uses the need_action mechanism, this field is set to true. Otherwise, it is false.
 - ``needaction_uid_ctr``: integer field. If the related model uses the need action mechanism, this field gives the number of actions the current user has to perform.

Those fields are functional, because they must be recalculated for each user, and each time menus are displayed. ``needaction_uid_ctr`` takes into account the domain of the action, in order to display accurate numbers.

Addon implementation example
++++++++++++++++++++++++++++

In your ``foo`` module, you want to specify that when it is in state ``confirmed``, it has to be validated by a manager, given by the field ``manager_id``. After making ``foo`` inheriting from ``base.needaction``, you override the ``get_needaction_user_ids`` method:

::

  [...]
  _inherit = [base.needaction]
  [...]
  def get_needaction_user_ids(self, cr, uid, ids, context=None):
    result = dict.fromkeys(ids)
    for foo_obj in self.browse(cr, uid, ids, context=context):
      # set the list void by default
      result[foo_obj.id] = []
      # if foo_obj is confirmed: manager is required to perform an action
      if foo_obj.state == 'confirmed':
        result[foo_obj.id] = [foo_obj.manager_id]
    return result
