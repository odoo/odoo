-- disable website_address_autocomplete
UPDATE website
SET google_places_api_key = 'dummy';
