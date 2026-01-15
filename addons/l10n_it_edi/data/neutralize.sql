-- neutralize Fattura Elettronica (FatturaPA)
UPDATE res_company
SET l10n_it_edi_register = false;
