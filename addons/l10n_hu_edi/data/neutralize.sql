-- disable l10n_hu edi integration
UPDATE l10n_hu_nav_communication
   SET state = 'draft' WHERE state = 'prod';
-- set every company to demo mode
UPDATE res_company
   SET l10n_hu_use_demo_mode = true;
