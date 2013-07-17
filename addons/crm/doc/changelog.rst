.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

- ``crm``, ``crm_claim``: removed inheritance from ``base_stage`` class. Missing
  methods have been added into ``crm`` and ``crm_claim``. Also removed inheritance
  in ``crm_helpdesk`` because it uses states, not stages.