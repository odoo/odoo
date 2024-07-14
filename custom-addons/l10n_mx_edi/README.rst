========================
EDI Mexican Localization
========================

Allow the user to generate the EDI document for Mexican invoicing.

This module allows the creation of the EDI documents and the communication with the Mexican certification providers (PACs) to sign/cancel them.

Usage
=====

Odoo Mexico Localization for Invoice with Custom Number
-------------------------------------------------------

This module extends the functionality of Mexican localization to support customs numbers when you generate the electronic invoice.

To use this module, you need to:

- Create a customer invoice normally.
- Add the personalized number related to the customs information, separated by commas,
  if there are several numbers for each line of the invoice associated with a product.

  For example, given the number of petition **16  52  3XXX  8000988**.

  The number of the corresponding request to import the good must be registered, which is integrated from left to right in the following way:

  Last 2 digits of the validation year followed by two spaces, 2 digits of the customs office followed by two spaces, 4 digits of the number of the patent followed by two spaces,
  1 digit corresponding to the last digit of the current year, except that it is of a consolidated motion, initiated in the immediately preceding year or of the original motion
  for a rectification, followed by 6 digits of the progressive numbering by customs.

  +------------+------------+---------+-----------+--------+------------+-----------------------+
  | Validation |            | Customs |           | Patent |            | Exercise and Quantity |
  +============+============+=========+===========+========+============+=======================+
  |     16     | Two Spaces |   52    | Two Space |  3XXX  | Two Spaces |       8000988         |
  +------------+------------+---------+-----------+--------+------------+-----------------------+

  With the previous value in the patent of our petition. These values must coincide with the SAT catalog in such a way that:

  * Validation: The year of validation. The value of positions one and two must be smaller or same as the last two digits of the year of the current date and must be greater or same as the last two digits of the year of the current date minus ten.

  * Customs: Code of customs clearance agent. Positions five and six must correspond to a key from the catalog of Customs (catCFDI: c_Aduana)

  * Patent: Positions nine through twelve must correspond to a patent number of the catalog of customs patents (catCFDI: c_PatenteAduanal)

  * Exercise: Last digit of the current year, unless it is of a consolidated motion, initiated in the immediately previous year or of the original motion for a rectification)

  * Quantity: The value of the last six digits must be between the minimum value 1 and the value maximum of consecutive numbers in the catalog quantity column catCFDI: c_NumPedimentoAduana that correspond to those used by customs in that year.

- Validate the invoice

For more information in the `SAT page <http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/cfdv33.pdf>`_. Page 70.
For more information in the SAT documentation

External Trade Complement for the Mexican localization
------------------------------------------------------

This module adds the External Trade Complement to CFDI version 4.0, in which
was added the customs information of the products, it specifies the emitter
and receiver address, and also data related to export laws.

This complement is required for all invoices where goods are exported and the
landing code is "A1"

The following fields were added in order to comply with complement structure
defined by the SAT.

- In the invoice:

  - **Need external trade?**: This field is used to indicate that in the CFDI
    document that will be generated, must be added the external trade
    complement. By default take this value from the partner, but could be
    changed here if is one exception. If this field is actived, then will be
    showed the next fields:

  - **Certificate Source**: If the document to be generated is a
    Certificate of Origin, must be registered the certificate of
    origin folio or the fiscal folio in CFDI with which the issuance of the
    certificate of origin was paid. If this field is empty, indicate that
    this document not funge as Certificate of Origin.


    .. figure:: ../l10n_mx_edi/static/src/InvoiceET.png

- In the product:

  - **Tariff Fraction**: This field is used to store the tariff fraction
    that corresponds to the product to be sold, this have loaded the SAT
    catalog "c_FraccionArancelaria_". If one record is not found is because
    only was loaded the current records.

  - **UMT Customs**: Field used to specify the key of the applicable unit
    of measure for the quantity expressed in the goods at customs. This
    unit of measure must correspond to the assigned Tariff Fraction in the
    product, as indicated in the SAT catalog.

  - **Weight**: If the *UMT Customs* is `KG`, here must be specific the weight
    of each product.


    .. figure:: ../l10n_mx_edi/static/src/Product_CET.png

- In Unit of measurement

  - **Customs Code**: Code that corresponding to the unit of measurement in the
    SAT's catalog. This is the code that use the aduana to the products
    related. Link_


    .. figure:: ../l10n_mx_edi/static/src/Code_Aduana.png

- In the invoice lines:

  - **Qty UMT**: It is the quantity expressed in the unit of measure of
    customs of the product.

    It will be used for the attribute "CantidadAduana" in each of the
    merchandise to sell, when the Code Customs of the product UMT is
    different to 99.

    This field is automatically filled in the invoice lines in the
    following cases:

    1. The product has the same value for UMT customs and UoM.
           In this case, Qty UMT is set to the same value of the quantity of
           products on the line.

    2. The code of the unit of measurement in UMT of the product is equal to 06 (kilo).
           In this case, Qty UMT will be equal to the weight defined in the
           product multiplied by the quantity of products being sold.

    In other cases, this value must be defined by the user, in each one of the
    lines.

  - **Unit Value UMT**: Represents the unit price of the merchandise in the
    Customs UMT. It is used to set the attribute "ValorUnitarioAduana" in
    each of the CFDI merchandise. It is transparent to the user.

  - **UMT Adduana**: This value by default is the same that is defined in the
    product of the line.


    .. figure:: ../l10n_mx_edi/static/src/invoice_line_ET.png
      :width: 700pt

- In the partner:

  - **Need external trade?**: Field used to indicate if the customer needs
    his/her invoices with external complement. If the field is equal to True,
    then the add-on is added to the CFDIs for this client.


    .. figure:: ../l10n_mx_edi/static/src/partnerET2.png

  - **Locality**: Field used to indicate the locality of the emitter and
    receiver in the CFDI

  - **Colony Code**: This field is used to store the emitter's code of the
    colony. It must be a value from the ones provided by the SAT's catalog.
    Note: This field only must be configured in the company address or in
    the partners that are used as branch address in multi-branch enviroments.
    c_colonia_

    .. figure:: ../l10n_mx_edi/static/src/partnerET.png

- In the Company

  - **Number of Reliable Exporter**: Identification of the exporter
    according to the Article 22 of Annex 1 of the Free Trade Agreement with
    the European Association and to the Decision of the European Community,
    used to establish the attribute "NumeroExportadorConfiable" if the
    country of the customer belongs to the Union European

- In addition, the following models were added:

  - **Locality**:  model used to store the localities from Mexico provided
    by the SAT's catalog. Its fields are name, state, country and code.
    c_localidad_

In this version, the external trade complement does not support the Type of
Transfer Proof ('T'). For this reason, the nodes "Propietario" and
"MotivodeTraslado" are not specified in the External Trade Template. On the
other hand, the optional node "DescripcionesEspecificas" will not be added
in this version, since it needs fields that depend on the stock module.
They will be added in a later version.

.. _c_FraccionArancelaria: http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/c_FraccionArancelaria.xls
.. _Link: http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/c_UnidadMedidaAduana.xls
.. _c_colonia: http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/c_Colonia.xls
.. _c_localidad: http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/c_Localidad.xls


Tax Cash Basis Entries at Payment Date
--------------------------------------

    Allow to create the Journal Entries for Taxes at date of payment.
    The following tests cases pretend to enlight you on what is expected of each
    one according to Mexican requirements.

    **Case Multi-currency (both invoice & payment) Payment before Invoice**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued yesterday in USD at a rate => 1MXN = 1 USD.
            Booked like:

                Receivable          1160                1160    USD
                    Revenue                 1000       -1000    USD
                    Taxes to Collect         160        -160    USD

            Payment issued two days ago in USD at a rate => 1MXN = 0.80 USD.
            Booked like:

                Bank                1450                1160    USD
                    Receivable              1450       -1160    USD

            This Generates a Exchange Rate Difference.
            Booked like:

                Receivable           290                   0    USD
                    Gain Exchange rate       290           0    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1250                1000    USD
                    Tax Base Account        1250       -1000    USD
                Taxes to Collect     200                 160    USD
                    Taxes to Paid            200        -160    USD

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 1250.00
                - Paid to SAT MXN 200.00
                - Have a difference of MXN 40.00 for Taxes to Collect that I would
                  later have to issue as a Loss in Exchange Rate Difference

                Loss Exchange rate    40                   0    USD
                    Taxes to Collect          40           0    USD


    **Case Multi-currency (both invoice & payment) Payment after Invoice**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued two days ago in USD at a rate => 1MXN = 0.80 USD.
            Booked like:

                Receivable          1450                1160    USD
                    Revenue                 1250       -1000    USD
                    Taxes to Collect         200        -160    USD

            Payment issued today in USD at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Bank                 928                1160    USD
                    Receivable               928       -1160    USD

            This Generates a Exchange Rate Difference.
            Booked like:

                Loss Exchange rate   522                   0    USD
                    Receivable               522           0    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account     800                1000    USD
                    Tax Base Account         800       -1000    USD
                Taxes to Collect     128                 160    USD
                    Taxes to Paid            128        -160    USD

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 800.00
                - Paid to SAT MXN 128.00
                - Have a difference of MXN -72.00 for Taxes to Collect that I would
                  later have to issue as a Gain in Exchange Rate Difference

                Taxes to Collect      72                   0    USD
                    Gain Exchange rate        72           0    USD


    **Case Multi-currency (both invoice & payment) Payment same day than Invoice**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued two days ago in USD at a rate => 1MXN = 0.8 USD.
            Booked like:

                Receivable          1450                1160    USD
                    Revenue                 1250       -1000    USD
                    Taxes to Collect         200        -160    USD

            Payment issued two days ago in USD at a rate => 1 MXN = 0.8 USD.
            Booked like:

                Bank                1450                1160    USD
                    Receivable              1450       -1160    USD

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1250                1000    USD
                    Tax Base Account        1250       -1000    USD
                Taxes to Collect     200                 160    USD
                    Taxes to Paid            200        -160    USD

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 1250.00
                - Paid to SAT MXN 200.00
                - Have no difference for Taxes to Collect


    **Case Invoiced Yesterday (MXN) Payment Two Days Ago (USD)**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued yesterday in MXN at a rate => 1MXN = 1 USD.
            Booked like:

                Receivable          1160                   -      -
                    Revenue                 1000           -      -
                    Taxes to Collect         160           -      -

            Payment issued two days ago in USD at a rate => 1 MXN = 0.80 USD.
            Booked like:

                Bank                1160                 928    USD
                    Receivable              1160        -928    USD

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1000                   0      -
                    Tax Base Account        1000           0      -
                Taxes to Collect     160                   0      -
                    Taxes to Paid            160           0      -

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 1000.00
                - Paid to SAT MXN 160.00
                - Have no difference for Taxes to Collect


    **Case Invoiced Yesterday (USD) Payment Today (MXN)**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued yesterday in USD at a rate => 1MXN = 1 USD.
            Booked like:

                Receivable          1160                1160    USD
                    Revenue                 1000       -1000    USD
                    Taxes to Collect         160        -160    USD

            Payment issued today in MXN at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Bank                 928                   -      -
                    Receivable               928           -      -

            This Generates a Exchange Rate Difference.
            Booked like:

                Loss Exchange rate   232                 232    USD
                    Receivable               232        -232    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account     800                   0    USD
                    Tax Base Account         800           0    USD
                Taxes to Collect     128                   0    USD  # (I'd expect the same value as in the invoice for amount_currency in tax: 160 USD)
                    Taxes to Paid            128           0    USD

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 800.00
                - Paid to SAT MXN 128.00
                - Have a difference of MXN -32.00 for Taxes to Collect that I would
                  later have to issue as a Gain in Exchange Rate Difference

                Taxes to Collect      32                   0    USD
                    Gain Exchange rate        32           0    USD


    **Case Invoiced Yesterday (MXN) Payment Today (MXN)**

            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued yesterday in MXN at a rate => 1MXN = 1 USD.
            Booked like:

                Receivable          1160                   -      -
                    Revenue                 1000           -      -
                    Taxes to Collect         160           -      -

            Payment issued today in MXN at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Bank                1160                   -      -
                    Receivable              1160           -      -

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1000                   -      -
                    Tax Base Account        1000           -      -
                Taxes to Collect     160                   -      -
                    Taxes to Paid            160           -      -

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 1000.00
                - Paid to SAT MXN 160.00
                - Have no difference for Taxes to Collect


    **Case Multi-currency (both invoice & payment) Payment before Invoice (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued yesterday in USD at a rate => 1MXN = 1 USD.
            Booked like:

                Expenses            1000                1000    USD
                Unpaid Taxes         160                 160    USD

                    Payable                 1160       -1160    USD

            Payment issued two days ago in USD at a rate => 1MXN = 0.80 USD.
            Booked like:

                Payable             1450                1160    USD
                    Bank                    1450       -1160    USD

            This Generates a Exchange Rate Difference.
            Booked like:

                Loss Exchange rate   290                   0    USD
                    Payable                  290           0    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1250                1000    USD
                    Tax Base Account        1250       -1000    USD
                Creditable Tax       200                 160    USD
                    Unpaid Taxes             200        -160    USD

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 1250.00
                - Creditable Tax MXN 200.00
                - Have a difference of MXN -40.00 for Unpaid Taxes that I would
                  later have to issue as a Loss in Exchange Rate Difference

                Unpaid Taxes          40                   0    USD
                    Gain Exchange rate        40           0    USD


    **Case Multi-currency (both invoice & payment) Payment after Invoice (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued two days ago in USD at a rate => 1MXN = 0.80 USD.
            Booked like:

                Expenses            1250                1000    USD
                Unpaid Taxes         200                 160    USD

                    Payable                 1450       -1160    USD

            Payment issued today in USD at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Payable              928                1160    USD
                    Bank                     928       -1160    USD

            This Generates a Exchange Rate Difference.
            Booked like:

                Payable              522                   0    USD
                    Gain Exchange rate       522           0    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account     800                1000    USD
                    Tax Base Account         800       -1000    USD
                Creditable Tax       128                 160    USD
                    Unpaid Taxes             128        -160    USD

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 800.00
                - Creditable Tax MXN 128.00
                - Have a difference of MXN 72.00 for Unpaid Taxes that I would
                  later have to issue as a Loss in Exchange Rate Difference

                Loss Exchange rate    72                   0    USD
                    Unpaid Taxes              72           0    USD


    **Case Multi-currency (both invoice & payment) Payment same day than Invoice (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued two days ago in USD at a rate => 1MXN = 0.8 USD.
            Booked like:

                Expenses            1250                1000    USD
                Unpaid Taxes         200                 160    USD

                    Payable                 1450       -1160    USD

            Payment issued two days ago in USD at a rate => 1 MXN = 0.8 USD.
            Booked like:

                Payable             1450                1160    USD
                    Bank                    1450       -1160    USD

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1250                1000    USD
                    Tax Base Account        1250       -1000    USD
                Creditable Tax       200                 160    USD
                    Unpaid Taxes             200        -160    USD

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 1250.00
                - Creditable Tax MXN 200.00
                - Have no difference for Unpaid Taxes


    **Case Invoiced Yesterday (MXN) Payment Two Days Ago (USD) (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued yesterday in MXN at a rate => 1MXN = 1 USD.
            Booked like:

                Expenses            1000                   -      -
                Unpaid Taxes         160                   -      -

                    Payable                 1160           -      -

            Payment issued two days ago in USD at a rate => 1 MXN = 0.80 USD.
            Booked like:

                Payable             1160                 928    USD
                    Bank                    1160        -928    USD

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1000                   0      -
                    Tax Base Account        1000           0      -
                Creditable Tax       160                   0      -
                    Unpaid Taxes             160           0      -

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 1000.00
                - Creditable Tax MXN 160.00
                - Have no difference for Unpaid Taxes


    **Case Invoiced Yesterday (USD) Payment Today (MXN) (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued yesterday in USD at a rate => 1MXN = 1 USD.
            Booked like:

                Expenses            1000                1000    USD
                Unpaid Taxes         160                 160    USD

                    Payable                 1160       -1160    USD

            Payment issued today in MXN at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Payable              928                   -      -
                    Bank                     928           -      -

            This Generates a Exchange Rate Difference.
            Booked like:

                Payable              232                 232    USD
                    Gain Exchange rate       522        -232    USD

            And a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account     800                   0    USD
                    Tax Base Account         800           0    USD
                Creditable Tax       128                   0    USD  # (I'd expect the same value as in the invoice for amount_currency in tax: 160 USD)
                    Unpaid Taxes             128           0    USD

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 800.00
                - Creditable Tax MXN 128.00
                - Have a difference of MXN 32.00 for Unpaid Taxes that I would
                  later have to issue as a Loss in Exchange Rate Difference

                Loss Exchange rate    32                   0    USD
                    Unpaid Taxes              32           0    USD


    **Case Invoiced Yesterday (MXN) Payment Today (MXN) (Supplier)**

            Test to validate tax effectively Payable

            My company currency is MXN.

            Invoice issued yesterday in MXN at a rate => 1MXN = 1 USD.
            Booked like:

                Expenses            1000                   -      -
                Unpaid Taxes         160                   -      -

                    Payable                 1160           -      -

            Payment issued today in MXN at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Payable             1160                   -      -
                    Bank                    1160           -      -

            This does not generates any Exchange Rate Difference.

            But a Tax Cash Basis Entry is generated.
            Booked like:

                Tax Base Account    1000                   -      -
                    Tax Base Account        1000           -      -
                Creditable Tax       160                   -      -
                    Unpaid Taxes             160           -      -

            What I expect from here:
                - Base to report to DIOT: Tax Base Account MXN 1000.00
                - Creditable Tax MXN 160.00
                - Have no difference for Unpaid Taxes


    **Case Invoiced Yesterday (MXN) Credit Note Today (MXN) (Customer)**
            Test to validate tax effectively receivable

            My company currency is MXN.

            Invoice issued two days ago in USD at a rate => 1MXN = 0.80 USD.
            Booked like:

                Receivable          1450                1160    USD
                    Revenue                 1250       -1000    USD
                    Taxes to Collect         200        -160    USD

            Credit Note issued today in USD at a rate => 1 MXN = 1.25 USD.
            Booked like:

                Revenue              800                1000    USD
                Taxes to Collect     128                 160    USD

                    Receivable               928       -1160    USD

            This Generates a Exchange Rate Difference.
            Booked like:

                Loss Exchange rate   522                   0    USD
                    Receivable               522           0    USD

            And two Tax Cash Basis Entry are generated.
            Booked like:

                Tax Base Account     800                1000    USD
                    Tax Base Account         800       -1000    USD
                Taxes to Collect     128                 160    USD
                    Taxes to Paid            128        -160    USD

                Tax Base Account     800                1000    USD
                    Tax Base Account         800       -1000    USD
                Taxes to Paid        128                 160    USD
                    Taxes to Collect         128        -160    USD

            What I expect from here:
                - Base to report to DIOT if it would be the case (not in this case):
                  * Tax Base Account MXN 800.00 and MXN -800.00
                - Paid to SAT MXN 0.00
                - Have a difference of MXN -72.00 for Taxes to Collect that I would
                  later have to issue as a Gain in Exchange Rate Difference

                Taxes to Collect      72                   0    USD
                    Gain Exchange rate        72           0    USD

EDI Cancellation
----------------

This module adds the next features in the cancel process:

1. Button to request cancellation in the SAT was added.
2. The cancel process in Odoo, only could be executed when the SAT status
   is cancelled.
3. The cancel button in the invoice is dummy if the invoice is not
   cancelled in the SAT.

**Which is the new flow to cancel?**

A new button `(Request Cancelation)` was added on the invoice view, that
appear when the invoice is open and the `PAC status` is `Signed`

When this new button is press, send the CFDI to the PAC to try cancel it
in the SAT system. And do not allows to cancel the invoice in Odoo until
it was properly canceled in the SAT. (This is an automatic action that
execute the system).

If any invoice is cancelled in the SAT, and the user can not wait for the
cron, could press the `Cancel` button, and this must be cancelled.

**Which are the cases supported in this module?**

**Case 1**

+----------+---------+
| System   | State   |
+==========+=========+
| Odoo     | Open    |
+----------+---------+
| PAC      | Signed  |
+----------+---------+
| SAT      | Valid   |
+----------+---------+

This case is when the invoice is properly signed in the SAT system. To
cancel is necessary to press the button `Request Cancelation`, that will
to verify that effectively the CFDI is not previously canceled in the SAT
system and will to send it to cancel in the SAT.

After of request the cancelation, could be found the next cases:

*The cancel process was succesful*

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Open       |
+----------+------------+
| PAC      | Cancelled  |
+----------+------------+
| SAT      | Valid      |
+----------+------------+

In this case, the system will execute the next actions:

1. An action will to update the PAC status (To Canceled).

2. A method will be called and will try to cancel the invoice in Odoo.


*The cancel process cannot be completed*

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Open       |
+----------+------------+
| PAC      | To Cancel  |
+----------+------------+
| SAT      | Valid      |
+----------+------------+

In this case, the system wait for the PAC system, and will execute the next
action:

1. A method will be called to verify if the CFDI was properly cancelled in
the SAT system, and when the SAT status is `Cancelled` will try to cancel the
invoice in Odoo.

**Case 2**

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Open       |
+----------+------------+
| PAC      | To Cancel  |
+----------+------------+
| SAT      | Valid      |
+----------+------------+

This case is the same that in the previous case when the cancel process
cannot be completed.

If the customer does not accept the CFDI cancelation, the cancel process
must be aborted and the invoice must be returned to signed. For this, was
added an action in the invoice `Revert CFDI cancellation`, that could be
called in the `Actions` of it.


**Case 3**

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Open       |
+----------+------------+
| PAC      | To Cancel  |
+----------+------------+
| SAT      | Cancelled  |
+----------+------------+

The system executes a scheduled action that will cancel the invoice in Odoo,
and in that process, the PAC status must be updated to `Cancelled`.


**Case 4**

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Cancel     |
+----------+------------+
| PAC      | Signed     |
+----------+------------+
| SAT      | Valid      |
+----------+------------+

The system executes a scheduled action that will check that the SAT status
continues `Valid` and if yes, the invoice must be returned to `Open`
(Without generate a new CFDI). For this:

1. If the invoice does not has a journal entry, a new will be generated and
the invoice state must be changed to `Open`.

2. If the journal entry in the invoice has a revert, it will be cancelled
and the invoice state must be changed to `Open`.

**Case 5**

+----------+------------+
| System   | State      |
+==========+============+
| Odoo     | Cancel     |
+----------+------------+
| PAC      | To Cancel  |
+----------+------------+
| SAT      | Valid      |
+----------+------------+

This is the same case that in the previous one, but extra after that the
invoice is open again, the PAC status must be updated to 'Signed.'
