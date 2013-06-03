.. _gamification_goal:

gamification.goal
=================

Models
++++++

``gamification.goal`` for the generated goals from plans

.. versionchanged:: 7.0

Fields
++++++

 - ``type_id`` : The related gamification.goal.type object.
 - ``user_id`` : The user responsible for the goal. Goal type domain filtering on the user id will use that value.
 - ``planline_id`` : if the goal is generated from a plan, the planline used to generate this goal
 - ``plan_id`` : if the goal is generated from a plan, related link from planline_id.plan_id
 - ``start_date`` : the starting date for goal evaluation. If a goal is evaluated using a date field (eg: creation date of an invoice), this field will be used in the domain. Without starting date, every past recorded data will be considered in the goal type computation.
 - ``end_date`` : the end date for goal evaluation, similar to start_date. When an end_date is passed, the goal update method will change to status to reached or failed depending of the current value.
 - ``target_goal`` : the numerical value to reach (higher or lower depending of goal type) to reach a goal
 - ``current`` : current computed value of the goal
 - ``completeness`` : percentage of completion of a goal
 - ``state`` : 
    - ``draft`` : goal not active and displayed in user's goal list. Only present for manual creation of goal as plans generate goals in progress.
    - ``inprogress`` : a goal is started and is not closed yet
    - ``inprogress_update`` : in case of manual goal, a number of day can be specified. If the last manual update from the user is older than this number of days, a reminder will be sent and the state changed to this.
    - ``reached`` : the goal is succeeded
    - ``failed`` : the goal is failed
    - ``canceled`` : state if the goal plan is canceled
 - ``remind_update_delay`` : the number of day before an inprogress goal is set to inprogress_update and a reminder is sent.
 - ``last_update`` : the date of the last modification of this goal
 - ``computation_mode`` : related field from the linked goal type
 - ``type_description`` : related field from the linked goal type
 - ``type_suffix`` : related field from the linked goal type
 - ``type_condition`` : related field from the linked goal type


Methods
+++++++

 - ``update`` :
   Compute the current value of goal and change states accordingly and send reminder if needed.
 - ``get_action`` :
   Returns the action description specified for the goal modification. If an action XML ID is specified in the goal type definition it will be used. If a goal is manual, the action is a simple wizard to input a new value.
