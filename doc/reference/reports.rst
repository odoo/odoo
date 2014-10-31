.. _reference/reports:

============
QWeb Reports
============

Paper Formats
-------------

There is a model called Paper Format allowing to define details specific to
the PDF output.  These details include margins, header line, ... Everything
related to the printed pdf.  Defining a paper format is not mandatory as there
is a default one set on the company.  If you want a specific report to be
associated to a specific paper format , just link the ir.actions.report.xml to
it.

Expressions used in Odoo report templates
-----------------------------------------

There are some magic variables used in the report rendering. The main ones are
the following:

``docs``
    records for the current report
``doc_ids``
    list of ids for the ``docs`` records
``doc_model``
    model for teh ``docs`` records
``time``
    a reference to time_ from the Python standard library
``translate_doc``
    a function to translate a part of a report. It must be used as follow:

    .. code-block:: xml

        <t t-foreach="doc_ids" t-as="doc_id">
          <t t-raw="translate_doc(doc_id, doc_model, 'partner_id.lang', account.report_invoice_document')"/>
        </t>
``user``
    ``res.user`` record for the user printing the report
``res_company``
    record the current ``user``'s company

Custom report
-------------

A generic report use the default rendering context, containing the magic
variables as explained before. If you want a new rendering context containing
anything you want to process your data Odoo AbstractModel, a custom module is
needed. These reports are called "particular report".

For a particular report, you have to write an Odoo Model containing a
render_html method.  Classically, this method returns a call to the original
**QWeb render** with a **custom rendering context**.

.. code-block:: python

    from openerp import api, models


    class ParticularReport(models.AbstractModel):
        _name = 'report.<<module.reportname>>'
        @api.multi
        def render_html(self, data=None):
            report_obj = self.env['report']
            report = report_obj._get_report_from_name('<<module.reportname>>')
            docargs = {
                'doc_ids': self._ids,
                'doc_model': report.model,
                'docs': self,
            }
            return report_obj.render('<<module.reportname>>', docargs)

.. _time: https://docs.python.org/2/library/time.html
