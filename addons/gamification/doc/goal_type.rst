.. _gamification_goal_type:

gamification.goal.type
======================

Models
++++++

``gamification.goal.type`` for the shared behaviour of goals

Fields
++++++

 - ``name`` : The name of the goal type.
 - ``description`` : Explain briefly in non-technical terms what the goal evaluates
 - ``computation_mode`` : How is computed the current value for each individual goal
    - ``manually`` : the user will set the value itself, no computation
    - ``count`` : the result is the number of lines returned by a search (eg: number of phone calls)
    - ``sum`` : the total of the value of a chosen field for each record returned by the search (eg: total amount of all invoices)
    - ``python`` : for complex computation, will execute a chosen method
 - ``display_mode`` : How is represented the current value of a goal
    - ``progress`` : numerical value (eg: an amount)
    - ``checkbox`` : boolean value with only two state: todo and done (eg: select a timezone)

 - ``suffix`` : text suffix added to the result
 - ``full_suffix`` : function field combining the monetary and suffix field (eg: €/month, $ expected)
 - ``model_id`` : the model to evaluate for count and sum goals (eg: Invoices)
 - ``field_id`` : for sum goals only, the field of model_id that will be evaluated through the computation
 - ``field_date_id`` : the date to evaluate to restrict the search on a time interval for count and sum goals (eg: validation date)
 - ``domain`` : Additional restrictions in the form of a domain. To restric the search to a user, use the keyword 'user', can be chained. Eg: ``[('state', '=', 'done'), ('user_id', '=', user.id)]`` or ``[('company_id', '=', user.company_id.id)]``
 - ``compute_code`` : for python goals only, the method of type gamification.goal.type to execute (eg: self.my_method(cr, uid))
 - ``condition`` : when is the goal considered as reacher
    - ``higher`` : when the current value is higher or equal than the target
    - ``lower`` : when the current value is smaller or equal than the target
 - ``sequence`` : to order list of goals in a challenger
 - ``action_id`` : the XML id to of an ir.actions.act_window to execute when the user clicks on a goal on the home page
 - ``res_id_field`` : the res_id used by the action, using user as for the domain (eg: user.company_id.id)

Methods
+++++++

Add new methods inheriting from this class to add goal type with python computation mode. Look at the example in ``gamification/goal_type_data.py``