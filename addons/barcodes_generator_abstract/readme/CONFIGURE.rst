To configure this module, you need to:

* Go to Settings / Technical / Sequences & Identifiers / Barcode Nomenclatures
* Select a Nomenclature
* Create or select a rule

.. image:: ../static/description/barcode_nomenclature_form.png

* For manual generation, set:
    * 'Base set Manually' in 'Generate Type'
    * Set the model

.. image:: ../static/description/barcode_rule_form_manual.png

* For automatic generation, set:
    * 'Base managed by Sequence' in 'Generate Type'
    * Set the model
    * Generate a new sequence by button, or affect a existing one

.. image:: ../static/description/barcode_rule_form_sequence.png

In all cases, padding will be computed automaticaly, based on the number
of '.' in the Barcode Pattern field.
