Edit the tree view and add the widget as the first field, usually, we should use:
.. code-block:: xml

    <field name="id" widget="open_tab"/>

You can open the record in a new tab when clicking with the mouse wheel on the external link icon.
On a usual click the record will be opened without changes (keeping the breadcrumbs).

You can also add open-tab field in tree views by selecting "Add Open Tab Field" field in
the ir.model record. When you do this, the open-tab field is added right after the name
field in the tree if the field exists, otherwise at the beginning of the tree.
