
========================================
OpenERP BI View (a.k.a. Graph View)
========================================

Outline
'''''''

* BI in Odoo
* Adding a Graph view
* Graph view parameters
* Fields: measures and dimensions
* Graph view architecture

BI in Odoo
''''''''''

The graph view gives a way to look at your data and to visualize it in various ways.  Currently, it supports four main modes:

* **pivot**: it is probably the most important mode.  It is a multidimensional table that you can configure to display any possible cube for your data.
* **bar**: displays a bar chart
* **pie**: displays a pie chart
* **line**: displays a line chart

The basic idea is that you can work in pivot table mode to select the desired dimensions, use the search bar to select appropriate filters, and switch to various chart modes when your data is ready.

**Note**: the technical name for the graph view is *web_graph*.

Fields: measures and dimensions
'''''''''''''''''''''''''''''''

To do its work, the graph view understands two kind of fields:

* **measure**: a measure is a field that can be aggregated (right now, the only aggregation method is the sum).  Every field of type *integer* or *float* (except the *id* field) can be used as a measure.
* **dimension**: A dimension is a field that can be grouped.  That means pretty much every non numeric fields.


When loading, the graph view reads the list of fields from the model.  The measures are then obtained from that list.  The dimensions are right now obtained from the *Group By* filters category defined in the search bar, but in a later release, the dimensions will be every groupable fields in the model.


**Note**: it is important to note that the fields value are obtained with the *read_group* method in the ORM.  It means that it directly reads from the database, and can not evaluate non-stored functional fields.  If you want to use functional fields as measure or dimension, make sure to store them in the database (with the *stored=true* attribute)


Adding a Graph View
'''''''''''''''''''

In general, the process to add a graph view is:

1. register a graph view in a xml file.  For example, this code registers a graph view for the model *project.task*.  The *graph* tag is where the graph view default parameters are defined.  These parameters will be explained in the next section.

.. code-block:: xml

        <record id="view_project_task_graph" model="ir.ui.view">
            <field name="name">project.task.graph</field>
            <field name="model">project.task</field>
            <field name="arch" type="xml">
                <graph string="Project Tasks" type="bar">
                    <field name="project_id" type="row"/>
                    <field name="planned_hours" type="measure"/>
                </graph>
            </field>
        </record>


2. Add the graph view to an action (of course, if there is no action yet, an action has to be created as well).  In this example, the *graph* value in the view_mode field is where the web client will see that a graph view as to be created when the action *action_view_task* is triggered.

.. code-block:: xml

    <record id="action_view_task" model="ir.actions.act_window">
        ...
        <field name="view_mode">kanban,tree,form,calendar,gantt,graph</field>
        ...

3. If necessary, force the correct view with its id.  The way the client operates is quite simple: it will pick the lowest priority available view for a given model.  If this behaviour is not what you need, you can force it with the *view_id* field:

.. code-block:: xml

        <field name="view_id" ref="view_project_task_graph"/>


Graph view parameters
''''''''''''''''''''''

In *graph* tag:
---------------

* string: title of the graph
* stacked: if bar chart is stacked/not stacked (default=false)
* type: mode (pivot, bar, pie, line) (default=bar).  This parameter determines the mode in which the graph view will be when it loads.  

The *type* attribute:
---------------------

The *graph* tag can contain a number of *field* subtags.  These fields should have a name attribute (corresponding to the name of a field in the corresponding model).  The other main attribute is *type*.  Here are its possible values:

* row : the field will be grouped by rows (dimension)
* col : the field will be grouped by cols (dimension)
* measure : the field will be aggregated
* if no type, measure by default

The order is important: for example if two fields are grouped by row, then the first one that appears in the xml description will be the first one used to group, and the second will be used as a way to define sub groups.

Date/datetime
-------------

Dates and datetimes are always a little tricky.  There is a special syntax for grouping them by intervals.  Most of the time, the interval can be specified as a suffix:

* field_date:day, 
* field_date:week, 
* field_date:month (default)
* field_date:quarter, 
* field_date:year

For example,

.. code-block:: xml

        <filter string="Week" context="{'group_by':'date_followup:week'}" help="Week"/>

But to describe a graph view in xml, this would fail the xml validation ("date_followup:week" is not a valid field).  In that case, the graph view can be described with an "interval" attribute.  For example, 

.. code-block:: xml

        <graph string="Leads Analysis" type="pivot" stacked="True">
            <field name="date_deadline" interval="week" type="row"/>
            <field name="stage_id" type="col"/>
            <field name="planned_revenue" type="measure"/>
        </graph>

Example:
--------
Here is an example of a graph view defined for the model *crm.lead.report*.  It will open in pivot table mode.  If it is switched to bar chart mode, the bars will be stacked.  The data will be grouped according to the date_deadline field in rows, and the columns will be the various stages of an opportunity.  Also, the *planned_revenue* field will be used as a measure.

.. code-block:: xml

    <record id="..." model="ir.ui.view">
        <field name="name">crm.opportunity.report.graph</field>
        <field name="model">crm.lead.report</field>
        <field name="arch" type="xml">
            <graph string="Leads Analysis" type="pivot" stacked="True">
                <field name="date_deadline" type="row"/>
                <field name="stage_id" type="col"/>
                <field name="planned_revenue" type="measure"/>
            </graph>
        </field>
    </record>

**Note**: the old graph view syntax still works (for example, operator="+"), but it is a good idea to use the new syntax whenever possible.



Graph view architecture
'''''''''''''''''''''''

Overview
--------

The general design of the graph view is quite simple.  It is basically a javascript addon, so it lives in the client.  When it needs data from the model, it makes an async request to the server (only read_group calls), and displays the result as soon as it gets it.  

So, it means that the aggregation is done by the database (hence the constraint that functional fields need to be stored).

Also, note that it is basically *lazy*: it only request the data that it needs.  For example, if you drill down in a pivot table, it will only request the data corresponding to the subgroups.


Graph view
----------

The graph view (addon *web_graph*) is actually made out of three parts:

* **pivot table**: this is the part that keeps the data in memory and takes care of calling the ORM with ajax calls.
* **graph widget**: this is a normal Odoo widget that takes care of displaying the data (the graph view is actually managed by a large widget) and interacting with the user 
* **graph view**: its task is to interact with the web client.  So, basically, it only needs to instantiate a graph widget, and communicating both ways with the search view and the widget.

Because of that design, it is possible (for example, in a client action) to display only a widget without the graph view.  The widget has the full power of a normal graph view.  

Cross-model BI
--------------

Due to its design, it is not possible to display a graph view for more than one model at a time.  A graph view is tied to one and only one model.

However, a workaround is to create a new model that contains all the necessary data.  That model can fetch its data from a postgres view (so, it can view, but not edit the data).  It means that you can define any desired field from any table.  However, be careful because doing so bypass the security checks from the ORM.

Right now, most reporting views work that way, by defining custom views.