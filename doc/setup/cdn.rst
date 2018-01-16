:banner: banners/cdn.jpg

========================================
Deploying with Content Delivery Networks
========================================

.. _reference/cdn/keycdn:

Deploying with KeyCDN_
======================

.. sectionauthor:: Fabien Meghazi

This document will guide you through the setup of a KeyCDN_ account with your
Odoo powered website.

Step 1: Create a pull zone in the KeyCDN dashboard
--------------------------------------------------

.. image:: cdn/keycdn_create_a_pull_zone.png
   :class: img-responsive

When creating the zone, enable the CORS option in the
:guilabel:`advanced features` submenu. (more on that later)

.. image:: cdn/keycdn_enable_CORS.png
   :class: img-responsive

Once done, you'll have to wait a bit while KeyCDN_ is crawling your website.

.. image:: cdn/keycdn_progressbar.png
   :class: img-responsive

.. note:: a new URL has been generated for your Zone, in this case it is
          ``http://pulltest-b49.kxcdn.com``

Step 2: Configure the odoo instance with your zone
--------------------------------------------------

In the Odoo back end, go to the :guilabel:`Website Settings`: menu, then
activate the CDN support and copy/paste your zone URL in the
:guilabel:`CDN Base URL` field.

.. image:: cdn/odoo_cdn_base_url.png
   :class: img-responsive

Now your website is using the CDN for the resources matching the
:guilabel:`CDN filters` regular expressions.

You can have a look to the HTML of your website in order to check if the CDN
integration is properly working.

.. image:: cdn/odoo_check_your_html.png
   :class: img-responsive


Why should I activate CORS?
---------------------------

A security restriction in some browsers (Firefox and Chrome at time of writing)
prevents a remotely linked CSS file to fetch relative resources on this same
external server.

If you don't activate the CORS option in the CDN zone, the more obvious
resulting problem on a default Odoo website will be the lack of font-awesome
icons because the font file declared in the font-awesome CSS won't be loaded on
the remote server.

Here's what you would see on your homepage in such a case:

.. image:: cdn/odoo_font_file_not_loaded.png
   :class: img-responsive

A security error message will also appear in the browser's console:

.. image:: cdn/odoo_security_message.png
   :class: img-responsive

Enabling the CORS option in the CDN fixes this issue.

.. _KeyCDN: https://www.keycdn.com
