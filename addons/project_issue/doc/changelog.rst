.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

- Stage/state update

  - ``project.issue``: removed inheritance from ``base_stage`` class and removed
    ``state`` field. Added ``date_last_stage_update`` field holding last stage_id
    modification. Updated reports.
