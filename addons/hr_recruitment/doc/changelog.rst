.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

- Stage/state update

  - ``hr.applicant``: removed inheritance from ``base_stage`` class and removed
    ``state`` field. Added ``date_last_stage_update`` field holding last stage_id
    modification. Updated reports.
  - ``hr.recruitment.stage``: removed ``state`` field.
