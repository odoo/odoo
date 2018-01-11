.. _changelog:

Changelog
=========

`trunk (saas-2)`
----------------

 - updated ``hr.holidays`` workflow. It now starts in ``confirm`` state. In
   ``confirm```and ``refuse`` a Reset to Draft has been added in view / workflow,
   allowing to edit the request. Added a ``can_reset`` computed field to enable
   this transition. A user can edit its own requests, or all requests if he is
   an Hr Manager.
