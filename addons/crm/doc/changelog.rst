.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

- Stage/state update

  - ``crm.phonecall``: removed inheritance towards ``base_state``.
  - ``crm.lead``: removed ``state`` field. Added ``date_last_stage_update`` field
    holding last stage_id modification. Updated reports.
  - ``crm.case.stage``: removed ``state`` field.

- ``crm``, ``crm_claim``: removed inheritance from ``base_stage`` class. Missing
  methods have been added into ``crm`` and ``crm_claim``. Also removed inheritance
  in ``crm_helpdesk`` because it uses states, not stages.