.. _stage_status:

Stage and Status
================

Stage
+++++

.. versionchanged:: 8.0 saas-2 state/stage cleaning

This revision removed the concept of state on hr.applicant objects. The ``state``
field has been totally removed and replaced by stages, using ``stage_id``.

Convention
++++++++++

A ``hr.recruitment.stage`` is ``new`` when it has the following properties:

 - ``sequence`` = 1

