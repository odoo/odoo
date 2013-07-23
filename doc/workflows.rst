.. _workflows:

Workflows
=========

A workflow is a directed graph where the nodes are called "activities" and the
arcs are called "transitions".

- Activities define work that should be done within the OpenERP server, such as
  changing the state of some records, or sending mails.

- Transitions control how the workflow will go from activities to activities.

When defining a workflow, one can attach conditions, signals, and triggers to
transitions, so that the behavior of the workflow can depend on user actions
(such as clicking on a button), changes to records, or arbitrary Python code.

XML definition
--------------

Defining a workflow with data files is straightforward: a record "workflow" is
needed together with records for the activities and the transitions. For
instance here is a simple sequence of two activities defined in XML::

    <record id="test_workflow" model="workflow">
        <field name="name">test.workflow</field>
        <field name="osv">test.workflow.model</field>
        <field name="on_create">True</field>
    </record>

    <record id="activity_a" model="workflow.activity">
        <field name="wkf_id" ref="test_workflow"/>
        <field name="flow_start">True</field>
        <field name="name">a</field>
        <field name="kind">function</field>
        <field name="action">print_a()</field>
    </record>
    <record id="activity_b" model="workflow.activity">
        <field name="wkf_id" ref="test_workflow"/>
        <field name="flow_stop">True</field>
        <field name="name">b</field>
        <field name="kind">function</field>
        <field name="action">print_b()</field>
    </record>

    <record id="trans_a_b" model="workflow.transition">
        <field name="act_from" ref="activity_a"/>
        <field name="act_to" ref="activity_b"/>
    </record>

A worfklow is always defined with respect to a particular model (the model is
given through the ``osv`` attribute on the ``workflow`` model). Methods
specified in the activities or transitions will be called on that model.

In the example code above, a workflow called "test_workflow" is created. It is
made up of two activies, named "a" and "b", and one transition, going from "a"
to "b".

The first activity has its ``flow_start`` attribute set to True so that OpenERP
knows where to start the workflow when it is instanciated. Because
``on_create`` is set to True on the workflow record, the workflow is
instanciated for each newly created record. (Otherwise, the workflow should be
created by other means, such as from some module Python code.)

When the workflow is instanciated, it will start by the "a" activity. That
activity is of kind ``function`` which means the action ``print_a()`` is a
method to be called on the ``test.workflow`` model (the usual ``cr, uid, ids,
context`` arguments are passed for you).

The transition between "a" and "b" does not specify any conditions. This means
the workflow instance will immediately progress from "a" to "b" (after "a" has
been processed), and thus elso process the "b" activity.

Conditions
----------

Triggers
--------

When an activity is completed, the workflow engine will try to get across
transitions departing from the completed activity, towards the next activities.
To get across a transition, its associated condition should evaluate to True.
If the condition evaluates to False, the transition is not taken (and thus the
activity it leads to will not be processed). Still, the workflow instance can
get new chances to progress across that transition by providing so-called
triggers. The idea is that when the condition fails, triggers (actually just
model name/record IDs pairs) are recorded in database. Later, it is possible to
wake-up specifically the workflow instances that installed those triggers,
offering them a new chance to evaluation their transition conditions. This
mechnism makes it cheaper to wake-up workflow instances by targetting just a
few of them (those that have installed the triggers) instead of all of them.

On each transition, in addition to a condition, records can be defined as a
trigger. The records will be defined as triggers as the transition is tried
withing a workflow, after the condition has failed. The actual records are
stored as model name and record ids. The model name is defined by the
trigger_model attribute of the transition while the record IDs are retrived by
evaluating the trigger_expression (also defined on the transition).

- I think the triggers are never deleted from the database. They are: they are
  'on delete cascade' on both the workflow instance and the workitem.

- Are those triggers re-installed whenever the transition is tried ? Nope.

