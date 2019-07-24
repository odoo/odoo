# -*- coding: utf-8 -*-
from . import models
"""
This multi-company sample module illustrates several coding principles
that should be respected so that errors are minimized when users work
in a multi-company environment.

It show several principles that should be shared accross most business flows:
- sanity checks for consistency regarding relationnal fields that belong
  to other companies are done at every step of the business flow (and not
  through constraints)
- models have coherent multi-company ir.rules
- m2o fields towards company records are used as the master information holder
  when setting domains on relational fields that target models that may be
  company-restricted; they have sensible defaults depending on the expected
  usage of the model
- models should prevent changing the company on a record if it could
  break business flows for other users of the system
- the 'force_company' context key is always set during company-sensitive
  CRUD operations since company-dependent fields must be read with the
  correct context to avoid faulty values

These are guidelines and designed to brought attention to recurring problems
when dealing with multi-company and that may get worse starting with Odoo 13
since multi-company has gotten a lot more permissive. These are not *laws*
and you should obviously think intensely about how this applies to your module/flow.
"""