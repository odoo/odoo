.. _howto/rdtraining/qwebintro:

=======================
A Brief History Of QWeb
=======================

Up to now, the design of the interface of our real estate module was rather limited. Building
a list view is straightforward since only the list of fields is necessary. The same holds true
for the forw view: despite the use of a few tags such as ``<group>`` or ``<page>``, there
is very little to do in terms of design.

However, if we want to give a unique look to our application, it is necessary to go a step
further and be able to design new views. Moreover, other features such as PDF reports or
website pages need another tool to be created with more flexibility: a templating_ engine.

You might already be familiar with existing engines such as Jinja (Python), ERB (Ruby) or
Twig (PHP). Odoo comes with its own built-in engine: :ref:`reference/qweb`.
QWeb is the primary templating engine used by Odoo. It is an XML templating engine and used
mostly to generate HTML fragments and pages.

Kanban views define the structure of each card as a mix of form elements
(including basic HTML) and :ref:`reference/qweb`.

Concrete Example: A Kanban View
===============================

.. _templating:
    https://en.wikipedia.org/wiki/Template_processor
