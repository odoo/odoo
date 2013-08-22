.. _stage_status:

Stage and Status
================

.. versionchanged:: 8.0 saas-2 state/stage cleaning

Stage
+++++

This revision removed the concept of state on crm.lead objects. The ``state``
field has been totally removed and replaced by stages, using ``stage_id``. The
following models are impacted:

 - ``crm.lead`` now use only stages. However conventions still exist about
   'New', 'Won' and 'Lost' stages. Those conventions are:

   - ``new``: ``stage_id and stage_id.sequence = 1``
   - ``won``: ``stage_id and stage_id.probability = 100 and stage_id.on_change = True``
   - ``lost``: ``stage_id and stage_id.probability = 0 and stage_id.on_change = True
     and stage_id.sequence != 1``

 - ``crm.case.stage`` do not have any ``state`` field anymore. 
 - ``crm.lead.report`` do not have any ``state`` field anymore. 

By default a newly created lead is in a new stage. It means that it will
fetch the stage having ``sequence = 1``. Stage mangement is done using the
kanban view or the clikable statusbar. It is not done using buttons anymore.

Stage analysis
++++++++++++++

Stage analysis can be performed using the newly introduced ``date_last_stage_update``
datetime field. This field is updated everytime ``stage_id`` is updated.

``crm.lead.report`` model also uses the ``date_last_stage_update`` field.
This allows to group and analyse the time spend in the various stages.

Open / Assignation date
+++++++++++++++++++++++

The ``date_open`` field meaning has been updated. It is now set when the ``user_id``
(responsible) is set. It is therefore the assignation date.

Subtypes
++++++++

The following subtypes are triggered on ``crm.lead``:

 - ``mt_lead_create``: new leads. Condition: ``obj.probability == 0 and obj.stage_id
   and obj.stage_id.sequence == 1``
 - ``mt_lead_stage``: stage changed. Condition: ``(obj.stage_id and obj.stage_id.sequence != 1)
   and obj.probability < 100``
 - ``mt_lead_won``: lead/oportunity is won. condition: `` obj.probability == 100
   and obj.stage_id and obj.stage_id.on_change``
 - ``mt_lead_lost``: lead/opportunity is lost. Condition: ``obj.probability == 0
   and obj.stage_id and obj.stage_id.sequence != 1'``


Those subtypes are also available on the ``crm.case.section`` model and are used
for the auto subscription.
