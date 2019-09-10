.. _changelog:

Changelog
=========

`trunk (saas-3)`
----------------

- ``hr.recruitment.stage``: added template_id field. If an email template is linked
  to the stage, it is used to render and post a message on the applicant. This
  allows for example to have template for accepted or refused applicants.

`trunk (saas-2)`
----------------

- Stage/state update

  - ``hr.applicant``: removed inheritance from ``base_stage`` class and removed
    ``state`` field. Added ``date_last_stage_update`` field holding last stage_id
    modification. Removed ``date`` field not used anywhere. Updated reports.
  - ``hr.recruitment.stage``: removed ``state`` field.

- Removed ``hired.employee`` wizard.
