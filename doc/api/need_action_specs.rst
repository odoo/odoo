Need action mixin class
=======================

This revision adds a mixin class for object implementing the need action mechanism. Need action mechanism can be used by objects that have to be able to signal that an action is required on a particular record. If in the business logic an action must be performed by somebody, for instance validation by a manager, this mechanism allows to set a field with the user_id of the user requested to perform the action.
    
Technically, this class adds a need_action_user_id field; when set to false, no action is required; when an user_id is set, this user has an action to perform. This field is a function field. Setting an user_id is done through redefining the get_needaction_user_id method. Therefore by redefining only one method, you can specify the cases in which an action will be required on a particular record.

This mechanism is used for instance to display the number of pending actions in menus, such as Leads (12).
