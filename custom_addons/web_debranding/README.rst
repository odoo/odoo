.. image:: https://itpp.dev/images/infinity-readme.png
   :alt: Tested and maintained by IT Projects Labs
   :target: https://itpp.dev

====================
 Backend debranding
====================

Build and enhance brand by removing references to `odoo.com <https://www.odoo.com/>`__ and customizing company logo, favicon, page title, etc.

1. *(feature is not required in 12.0+ versions)*
2. Replaces **Odoo** in page title
3. Replaces **Odoo** in help message for empty list
4. *(feature is not required in 9.0+ versions)*
5. Deletes Documentation, Support, About links from the top right-hand User Menu.
6. *(feature is not required in 11.0+ versions)*
7. Replaces **Odoo** in Dialog Box
8. Replaces **Odoo** in strings marked for translation
9. Replaces default favicon to a custom one (it applies for new companies only, otherwise you should change it manually)
10. *Hides Apps menu* (related `access_apps` module is excluded from dependencies since Odoo v15.0 and must be installed explicitly)
11. Disables server requests to odoo.com (publisher_warranty_url) - optional. Works only for non-enterprise versions of odoo
12. *(feature is a part of p.5)*
13. *(feature is not required in 13.0+ versions)*
14. *(feature is not required in 12.0+ versions)*
15. *(feature is not required in 12.0+ versions)*
16. *(feature is not required in 12.0+ versions)*
17. *(feature is not required in 15.0+ versions)*
18. Hides Enterprise features in Settings
19. Replaces **Odoo** in all backend qweb templates
20. Replaces **odoo.com** in hints, examples, etc.
21. Renames **OdooBot** to *Bot*. (Bot's avatar is not changed since Odoo v15, because one can change it manually via Bot User)
22. *(feature is not required in 15.0+ versions)*
23. Replaces links to `documentation <https://www.odoo.com/documentation>`__ (e.g. "Help" in Import tool, "How-to" in paypal, etc.) to custom website
24. *(feature is not required in 12.0+ versions)*
25. *(feature is not required in 12.0+ versions)*
26. Deletes Google Play, Apps Store apps links
27. *(feature in deleted in favor of OCA module mail_debrand)*
28. Deletes **Powered by Odoo** in Website (when installed)
29. Hides iap links in Settings


Roadmap
=======

* TODO: replace hardcoded placeholders and make them based on `web_debranding.new_website`
* TODO: support debranding in `--dev=xml` mode

Questions?
==========

To get an assistance on this module contact us by email :arrow_right: help@itpp.dev

Contributors
============
* `Ivan Yelizariev <https://it-projects.info/team/yelizariev>`__


Further information
===================

Odoo Apps Store: https://www.odoo.com/apps/modules/17.0/web_debranding/

Notifications on updates: `via Atom <https://github.com/itpp-labs/misc-addons/commits/14.0/web_debranding.atom>`_, `by Email <https://blogtrottr.com/?subscribe=https://github.com/itpp-labs/misc-addons/commits/14.0/web_debranding.atom>`_

Tested on `Odoo 17.0 <https://github.com/odoo/odoo/commit/40b19d89846303016098840f4958fe7cc105067c>`_
