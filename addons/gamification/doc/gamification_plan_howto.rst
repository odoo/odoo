How to create new challenge for my addon
========================================

Running example
+++++++++++++++

A module to create and manage groceries lists has been developped. To motivate users to use it, a challenge (gamification.goal.plan) is developped. This how to will explain the creation of a dedicated module and the XML file for the required data.

Module
++++++

The challenge for my addon will consist of an auto-installed module containing only the definition of goals. Goal type are quite technical to create and should not be seen or modified through the web interface.

If our groceries module is called ``groceries``, the structure will be consisted of three addons :

::

  addons/
    ...
    gamification/
    groceries/
    groceries_gamification/
      __openerp__.py
      groceries_goals.xml

The ``__openerp__.py`` file containing the following information :

::

  {
    ...
    'depends': ['gamification','groceries'],
    'data': ['groceries_goals.xml'],
    'auto_install': True,
  }


Goal type definition
+++++++++++++++++++++

For our groceries module, we would like to evaluate the total number of items written on lists during a month. The evaluated value being a number of line in the database, the goal type computation mode will be ``count``. The XML data file will contain the following information :

::

  <record model="gamification.goal.type" id="type_groceries_nbr_items">
    <field name="name">Number of items</field>
    <field name="computation_mode">count</field>
    ...
  </record>

To be able to compute the number of lines, the model containing groceries is required. To be able to refine the computation on a time period, a reference date field should be mention. This field date must be a field of the selected model. In our example, we will use the ``gorceries_item`` model and the ``shopping_day`` field.

::

  <record model="gamification.goal.type" id="type_groceries_nbr_items">
    ...
    <field name="model_id" eval="ref('groceries.model_groceries_item')" />
    <field name="field_date_id" eval="ref('groceries.field_groceries_item_shopping_day')" />
  </record>

As we do not want to count every recorded item, we will use a domain to restrict the selection on the user (display the count only for the items the users has bought) and the state (only the items whose list is confirmed are included). The user restriction is made with the keyword ``user_id`` in the domain and should correspond to a many2one field with the relation ``res.users``. During the evaluation, it is replaced by the user ID of the linked goal.

::

  <record model="gamification.goal.type" id="type_groceries_nbr_items">
    ...
    <field name="domain">[('shopper_id', '=', user_id), ('list_id.state', '=', 'confirmed')]</field>
  </record>

An action can also be defined to help users to quickly reach the screen where they will be able to modify their current value. This is done by adding the XML ID of the ir.action we want to call. In our example, we would like to open the grocery list form view owned by the user.

If we do not specify a res_id to the action, only the list of records can be displayed. The restriction is done with the field ``res_id_field`` containing the field name of the user profile containing the required id. In our example, we assume the res.users model has been extended with a many2one field ``groceries_list`` to the model ``groceries.list``.

::

  <record model="gamification.goal.type" id="type_groceries_nbr_items">
    ...
    <field name="action_id">groceries.action_groceries_list_form</field>
    <field name="res_id_field">groceries_list.id</field>
  </record>


Plan definition
++++++++++++++++

Once all the goal types are defined, a challenge (or goal plan) can be created. In our example, we would like to create a plan "Discover the Groceries Module" with simple tasks applied to every new user in the group ``groceries.shoppers_group``. This goal plan should only be applied once by user and with no ending period, no dates or peridocity is then selected. The goal will be started manually but specifying a value to ``start_date`` can make it start automatically.

::

  <record model="gamification.goal.plan" id="plan_groceries_discover">
    <field name="name">Discover the Groceries Module</field>
    <field name="period">once</field>
    <field name="visibility_mode">progressbar</field>
    <field name="report_message_frequency">never</field>
    <field name="planline_ids" eval="[(4, ref('planline_groceries_discover1'))]"/>
    <field name="autojoin_group_id" eval="ref('groceries.shoppers_group')" />
  </record>

To add goal types to a plan, planlines must be created. The value to reach is defined for a planline, this will be the ``target_goal`` for each goal generated.

::

  <record model="gamification.goal.planline" id="planline_groceries_discover1">
    <field name="type_id" eval="ref('type_groceries_nbr_items')" />
    <field name="target_goal">3</field>
    <field name="plan_id" eval="ref('plan_groceries_discover')" />
  </record>