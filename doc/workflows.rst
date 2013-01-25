.. _workflows:

Workflows
=========

- Low-level workflow functions (i.e. the openerp.workflow "service").
  Useful when looking-up a model and its records is not necessary, i.e. when
  working with raw model name and record ids is preferred (less hit to the
  database). Cannot really be used as it would bypass the ORM methods.
- Model-level (ORM) methods.
- XML-RPC endpoint and methods.

- Blah Model.signal_xxxx()
