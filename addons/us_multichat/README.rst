===============
 Customer Chat
===============

Base module to implement Live Chat through different channels (Telegram, WhatsApp, Viber, etc.).

Usage
=====

Add following code to your module. Replace MODULE and NAME for your custom values, e.g.

* `MODULE` is `us_telegram`
* `NAME` is `telegram`


MODULE/__manifest__.py
----------------------

.. code-block:: py

    "depends": ["multi_livechat"],
    "assets": {
        "web.assets_backend": [
            "MODULE/static/src/models/discuss/discuss.js",
            "MODULE/static/src/models/discuss_sidebar_category/discuss_sidebar_category.js",
        ],
    },


MODULE/models/__init__.py
-------------------------

.. code-block:: py

    from . import res_users_settings
    from . import mail_channel


MODULE/models/res_users_settings.py
-----------------------------------

.. code-block:: py

    from odoo import fields, models

    
    class ResUsersSettings(models.Model):
        _inherit = 'res.users.settings'
    
        is_discuss_sidebar_category_NAME_open = fields.Boolean("Is category NAME open", default=True)


MODULE/models/mail_channel.py
-----------------------------

.. code-block:: py

    from odoo import fields, models


    class MailChannel(models.Model):
        _inherit = "mail.channel"

        channel_type = fields.Selection(
            selection_add=[("multi_livechat_NAME", "Channel Description")],
            ondelete={"multi_livechat_NAME": "cascade"}
        )

MODULE/static/src/models/discuss.js
-----------------------------------

.. code-block:: js

    /** @odoo-module **/
    
    import { registerPatch } from '@mail/model/model_core';
    import { one } from '@mail/model/model_field';
    
    registerPatch({
        name: 'Discuss',
        fields: {
            categoryMLChat_echo_demo: one('DiscussSidebarCategory', {
                default: {},
                inverse: 'discussAsMLChat_NAME',
            }),
        },
    });


MODULE/static/src/models/discuss_sidebar_category.js
----------------------------------------------------

.. code-block:: js

    /** @odoo-module **/
    
    import { registerPatch } from '@mail/model/model_core';
    import { one } from '@mail/model/model_field';
    import { clear } from '@mail/model/model_field_command';
    
    registerPatch({
        name: 'DiscussSidebarCategory',
        fields: {
            categoryItemsOrderedByLastAction: {
                compute() {
                    if (this.discussAsMLChat_NAME) {
                        return this.categoryItems;
                    }
                    return this._super();
                },
            },
            discussAsMLChat_NAME: one('Discuss', {
                identifying: true,
                inverse: 'categoryMLChat_NAME',
            }),
            isServerOpen: {
                compute() {
                    // there is no server state for non-users (guests)
                    if (!this.messaging.currentUser) {
                        return clear();
                    }
                    if (!this.messaging.currentUser.res_users_settings_id) {
                        return clear();
                    }
                    if (this.discussAsMLChat_NAME) {
                        return this.messaging.currentUser.res_users_settings_id.is_discuss_sidebar_category_NAME_open;
                    }
                    return this._super();
                },
            },
            name: {
                compute() {
                    if (this.discussAsMLChat_NAME) {
                        return this.env._t("NAME");
                    }
                    return this._super();
                },
            },
            orderedCategoryItems: {
                compute() {
                    if (this.discussAsMLChat_NAME) {
                        return this.categoryItemsOrderedByLastAction;
                    }
                    return this._super();
                },
            },
            serverStateKey: {
                compute() {
                    if (this.discussAsMLChat_NAME) {
                        return 'is_discuss_sidebar_category_NAME_open';
                    }
                    return this._super();
                },
            },
            supportedChannelTypes: {
                compute() {
                    if (this.discussAsMLChat_NAME) {
                        return ['NAME'];
                    }
                    return this._super();
                },
            },
        },
    });


