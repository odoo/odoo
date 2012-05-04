Need action mechanism
=====================

.. versionadded:: 7.0

ir.needaction_mixin class
+++++++++++++++++++++++++

.. versionadded:: openobject-server.4124

This revision adds a mixin class for objects using the need action feature.

Need action feature can be used by objects willing to be able to signal that an action is required on a particular record. If in the business logic an action must be performed by somebody, for instance validation by a manager, this mechanism allows to set a list of users asked to perform an action.

This class wraps a class (ir.ir_needaction_users_rel) that behaves like a many2many field. However, no field is added to the model inheriting from ir.needaction_mixin. The mixin class manages the low-level considerations of updating relationships. Every change made on the record calls a method that updates the relationships.

Objects using the need_action feature should override the ``get_needaction_user_ids`` method. This methods returns a dictionary whose keys are record ids, and values a list of user ids, like in a many2many relationship. Therefore by defining only one method, you can specify if an action is required by defining the users that have to do it, in every possible situation.

This class also offers several global services,:
 - ``needaction_get_record_ids``: for the current model and uid, get all record ids that ask this user to perform an action. This mechanism is used for instance to display the number of pending actions in menus, such as Leads (12)
 - ``needaction_get_action_count``: as ``needaction_get_record_ids`` but returns only the number of action, not the ids (performs a search with count=True)
 - ``needaction_get_user_record_references``: for a given uid, get all the records that ask this user to perform an action. Records are given as references, a list of tuples (model_name, record_id).

.. versionadded:: openobject-server.4137

This revision of the needaction_mixin mechanism slighty modifies the class behavior. The ``ir_needaction_mixin`` class now adds a function field on models inheriting from the class. This field allows to state whether a given record has a needaction for the current user. This is usefull if you want to customize views according to the needaction feature. For example, you may want to set records in bold in a list view if the current user has an action to perform on the record. This makes the class not a pure abstract class, but allows to easily use the action information. The field definition is::


    def get_needaction_pending(self, cr, uid, ids, name, arg, context=None):
        res = {}
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, ids, context=context)
        for id in ids:
            res[id] = uid in needaction_user_ids[id]
        return res
    
    _columns = {
        'needaction_pending': fields.function(get_needaction_pending, type='boolean',
                        string='Need action pending',
                        help='If True, this field states that users have to perform an action. \
                                This field comes from the needaction mechanism. Please refer \
                                to the ir.needaction_mixin class.'),
    }

ir.needaction_users_rel class
+++++++++++++++++++++++++++++

.. versionadded:: openobject-server.4124

This class essentially wraps a database table that behaves like a many2many.
It holds data related to the needaction mechanism inside OpenERP. A row 
in this model is characterized by:

  - ``res_model``: model of the record requiring an action
  - ``res_id``: ID of the record requiring an action
  - ``user_id``: foreign key to the res.users table, to the user that
    has to perform the action

This model can be seen as a many2many, linking (res_model, res_id) to  
users (those whose attention is required on the record)

Menu modification
+++++++++++++++++

.. versionchanged:: openobject-server.4137

This revision adds three functional fields to ``ir.ui.menu`` model :
 - ``uses_needaction``: boolean field. If the menu entry action is an act_window action, and if this action is related to a model that uses the need_action mechanism, this field is set to true. Otherwise, it is false.
 - ``needaction_uid_ctr``: integer field. If the target model uses the need action mechanism, this field gives the number of actions the current user has to perform.
 - **REMOVED** ``needaction_record_ids``: many2many field. If the target model uses the need action mechanism, this field holds the ids of the record requesting the user to perform an action. **This field has been removed on version XXXX**.

Those fields are functional, because they depend on the user and must therefore be computed at every refresh, each time menus are displayed. The use of the need action mechanism is done by taking into account the action domain in order to display accurate results. When computing the value of the functional fields, the ids of records asking the user to perform an action is concatenated to the action domain. A counting search is then performed on the model, giving back the number of action the users has to perform, limited to the domain of the action.

Addon implementation example
++++++++++++++++++++++++++++

In your ``foo`` module, you want to specify that when it is in state ``confirmed``, it has to be validated by a manager, given by the field ``manager_id``. After making ``foo`` inheriting from ``ir.needaction_mixin``, you override the ``get_needaction_user_ids`` method:

::

  [...]
  _inherit = [`ir.needaction_mixin]
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
