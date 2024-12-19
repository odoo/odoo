`3.0.0`
--------

- **Fix:** module installation was crashed because of `recent update in Odoo v16 <https://github.com/odoo/odoo/pull/116368>`__

`2.0.2`
--------

- **Fix:** fix error 'NoneType' object has no attribute 'cr'. It happens under following conditions: website module is installed and `--db-filter` is not set.


`2.0.1`
--------

- **Fix:** delete obsolete code related to dropped feature about bot's avatar. That code caused an error on clicking chat icon
- **Fix:** error on using custom selection field

`2.0.0`
--------

- **Improvement:** make some features optional: access to Settings and Apps menus, restricted administration rights.
- **Improvement:** `web_debranding.new_documentation_website` is now full link to the documentation, i.e. `/documentation/` path is not mandatory anymore. Also, use official docs by default
- **Improvement:** bot's avatar is not changed on module installation and can be customized manually via Users menu

`1.1.1`
--------

- **Fix:** Debrand "session expired" popup

`1.1.0`
--------

- **New:** delete iap links in Settings
- **Fix:** hide Enterprise checkboxes in Settings

`1.0.32`
--------

- **Fix:** add missing dependency ``mail_bot``

`1.0.31`
--------

- **Fix:** delete Odoo placeholders in user's preferences

`1.0.30`
--------

- **Fix:** delete "Powered by Odoo" in website

`1.0.29`
--------

- **Fix:** error in Discuss menu on first usage

`1.0.28`
--------

**Fix:** debrand_bytes now accepts bytes and str types
**Fix:** fixed "OdooBot has a request" item in notifications
**Fix:** included mail_channel fixes

`1.0.27`
--------

**Fix:** error on res.config form opening

`1.0.26`
--------

- FIX: developer mode was availabile via dropdown menu for non-admins

`1.0.25`
--------

- FIX: error in Planner

`1.0.24`
--------

- FIX: Save\Create button didn't react in ``Point of Sale`` records

`1.0.23`
--------

- FIX: Debranding problems after introducing new features

`1.0.22`
--------

- FIX: method create didn't work via xmlrpc (e.g. on using Mail Composer)

`1.0.21`
--------

- FIX: In some cases, default parameters were used instead of custom ones

`1.0.20`
--------

- FIX: Hiding a custom logo
- FIX: Error when creating second empty database
- FIX: Remove official videos in planner
- FIX: Replace "Odoo" in 'install aplication' mails
- FIX: Remove Enterprise radio-buttons in Settings

`1.0.19`
--------

- FIX: Page title was empty even when it doesn't contain references to odoo

`1.0.18`
--------

- FIX: Replace icons for android and apple devices with custom url

`1.0.17`
--------

- FIX: Do not reset config values to default ones after upgrade or reinstall the module

`1.0.16`
--------

- FIX: Removed odoo.com link from left bottom of the page

`1.0.15`
--------

- FIX: Updating Title didn't work on *Optimize SEO* website tool

`1.0.14`
--------

- FIX: Compatibility with Timesheet Grid View module

`1.0.13`
--------

- IMP: Add "Developer mode" link to the top right-hand User Menu

`1.0.12`
--------

- FIX: Forbid to disable odoo.com binding for enterprise due to terms of Odoo Enterprise Subscription Agreement

`1.0.11`
--------

- FIX desktop notifications: replace odoo icon company log and debrand text

`1.0.10`
--------

- FIX: Reconsile button didn't work
- FIX: Updated title was not set

`1.0.9`
-------

- FIX: don't hide whole section in Settings if it not all fields are enterprise

`1.0.8`
-------

- IMP: 11. Disables server requests to odoo.com (publisher_warranty_url) - optional

`1.0.7`
-------

- FIX: bug with fields on User form in Odoo Enterprise

`1.0.6`
-------

- FIX: bug with replacing the word "odoo" in JS functions
- FIX: replace title and favicon in Odoo Enterprise


`1.0.5`
-------

- ADD: Replaces "Odoo" in all backend qweb templates (e.g. FAQ in import tool)

`1.0.4`
-------

- ADD: hide Enterprise features in Settings

`1.0.3`
-------

- ADD: support Enterprise release
- ADD: 16. Deletes "Odoo" in a request message for permission desktop notifications
- ADD: 17. [ENTERPRISE] Deletes odoo logo in application switcher


`1.0.2`
-------

- ADD: debrand Planner
- FIX: updates for recent odoo 9.0

`1.0.1`
-------

- FIX: updates for recent odoo 9.0
- REF: compatible with other Dashboard modules

`1.0.0`
-------

- init version
