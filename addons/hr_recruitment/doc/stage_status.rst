.. _stage_status:

Stage and Status
================

.. versionchanged:: 8.0 saas-2 state/stage cleaning

Stage
+++++

This revision removed the concept of state on hr.applicant objects. The ``state``
field has been totally removed and replaced by stages, using ``stage_id``. The
following models are impacted:

 - ``hr.applicant`` now use only stages. However a convention still exists about
   'New' stage. An applicant is consdered as ``new`` when it has the following
   properties:

   - ``stage_id and stage_id.sequence = 1``

 - ``hr.recruitment.stage`` do not have any ``state`` field anymore. 
 - ``hr.recruitment.report`` do not have any ``state`` field anymore. 

By default a newly created applicant be in a new stage. It means that it will
fetch the stage having ``sequence = 1``. Stage mangement is done using the
kanban view or the clikable statusbar. It is not done using buttons anymore.
Employee creation is still feasible directly from a link button in the form view.

Stage analysis
++++++++++++++

Stage analysis can be performed using the newly introduced ``date_last_stage_update``
datetime field. This field is updated everytime ``stage_id`` is updated.

``hr.recruitment.report`` model also uses the ``date_last_stage_update`` field.
This allows to group and analyse the time spend in the various stages.

Open / Assignation date
+++++++++++++++++++++++

The ``date_open`` field meaning has been updated. It is now set when the ``user_id``
(responsible) is set. It is therefore the assignation date.

Subtypes
++++++++

The following subtypes are triggered on ``hr.applicant``:

 - ``mt_applicant_new``: new applicants. Condition: ``obj.stage_id and obj.stage_id.sequence == 1``
 - ``mt_applicant_stage_changed``: stage changed. Condition: ``obj.stage_id and obj.stage_id.sequence != 1``

The following subtype is trigerred on ``hr.job``:

 - ``mt_job_new_applicant``: new applicant in the job.
