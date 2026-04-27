-- disable Employment Hero integration
UPDATE res_company
   SET employment_hero_enable = false,
       employment_hero_identifier = '',
       employment_hero_api_key = '';
