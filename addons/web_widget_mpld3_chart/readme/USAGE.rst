To insert a mpld3 chart in a view proceed as follows:

#. You should inherit from abstract class abstract.mpld3.parser::

    _name = 'res.partner'
    _inherit = ['res.partner', 'abstract.mpld3.parser']

#. Import the required libraries::

    import matplotlib.pyplot as plt

#. Declare a json computed field like this::

    mpld3_chart = fields.Json(
        string='Mpld3 Chart',
        compute='_compute_mpld3_chart',
    )

#. In its computed method do::

    def _compute_mpld3_chart(self):
        for rec in self:
            # Design your mpld3 figure:
            plt.scatter([1, 10], [5, 9])
            figure = plt.figure()
            rec.mpld3_chart = self.convert_figure_to_json(figure)

#. In the view, add something like this wherever you want to display your
   mpld3 chart::

    <div>
        <field name="mpld3_chart" widget="mpld3_chart" nolabel="1"/>
    </div>
