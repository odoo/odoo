.. highlight:: xml

Generic templates
=================

Generic template names should be prefixed by ``ui.`` to indicate their
special role.

Global Header: ``ui.Header``
----------------------------

Role
++++

This template is mostly dedicated to client actions taking over the
whole content area, and full-HTML form views (especially those opening
in the ``inline`` target).

It is used to display a buttons container (and can also be used for
status bars). The buttons should simply be placed inside the
``ui.Header`` body.

Arguments
+++++++++

The template only uses its body as argument.

Example
+++++++

::

    <t t-call="ui.Header">
        <button string="Apply" type="object" name="execute" class="oe_highlight"/>
        or
        <button string="Cancel" type="object" name="cancel" class="oe_link"/>
    </t>

This block demonstrates a common pattern in OpenERP views and widgets:
a highlighted button, and a discard button styled as a link to cancel
the action:

.. image:: ./images/templates/ui.Header.*

In this case, both buttons are OpenERP action buttons.
