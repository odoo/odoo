.. code-block:: python

    @api.model
    def method_name(self):
        values = [
            ('value_a', 'Title A'),
        ]
        if self.env.context.get('depending_on') == True:
            values += [
                ('value_b', 'Title B'),
            ]
        return values

.. code-block:: xml

    <field
        name="other_field"
    />
    <field
        name="char_field"
        widget="dynamic_dropdown"
        options="{'values':'method_name'}"
        context="{'depending_on': other_field}"
    />
