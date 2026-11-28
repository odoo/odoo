-- print every document of a neutralized database as a training document,
-- so that none passes for one issued under the company's real AT series
UPDATE l10n_pt_at_series
   SET training_series = true
 WHERE training_series IS NOT TRUE;
