Readme
======

`ep_disable_init_focus` is a very simple
[Etherpad-lite](https://github.com/ether/etherpad-lite) plugin, which disable
the focus on the pad content after its loading.

Rationale
---------

Etherpad-lite autofocus can be annoying to end-users when it is used in Odoo's
"pad" widget, because it will override web client focus rules. This plugin is
design to get rid of this behavior.


Installation instructions
-------------------------

1. Stop your Etherpad-lite server.
2. Copy the `ep_disabl_init_focus` folder into the `node_modules` folder of
   your Etherpad-lite installation.
3. in the folder of your Etherpad-lite installation, run this command to
   install the plugin:

    ```sh
    npm install node_modules/ep_disable_init_focus/
    ```
4. Restart the Etherpad-lite server.
