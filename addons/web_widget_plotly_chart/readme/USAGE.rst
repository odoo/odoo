To insert a Plotly chart in a view proceed as follows:

#. Declare a text computed field like this::

    plotly_chart = fields.Text(
        string='Plotly Chart',
        compute='_compute_plotly_chart',
    )

#. In its computed method do::

    def _compute_plotly_chart(self):
        for rec in self:
            data = [{'x': [1, 2, 3], 'y': [2, 3, 4]}]
            rec.plotly_chart = plotly.offline.plot(data,
                                         include_plotlyjs=False,
                                         output_type='div')

#. In the view, add something like this wherever you want to display your
   plotly chart::

    <div>
        <field name="plotly_chart" widget="plotly_chart" nolabel="1"/>
    </div>
