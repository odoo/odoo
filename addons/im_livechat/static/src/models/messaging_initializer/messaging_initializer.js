/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';
import { create, insert } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.messaging_initializer', 'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     * @param {object} mailUserSettings
     * @param {boolean} mailUserSettings.is_discuss_sidebar_category_livechat_open
     */
    _initMailUserSettings({ is_discuss_sidebar_category_livechat_open }) {
        this.messaging.discuss.update({
            categoryLivechat: create({
                counterComputeMethod: 'unread',
                displayName: this.env._t("Livechat"),
                isServerOpen: is_discuss_sidebar_category_livechat_open,
                serverStateKey: 'is_discuss_sidebar_category_livechat_open',
                sortComputeMethod: 'last_action',
                supportedChannelTypes: ['livechat'],
            }),
        });
        this._super(...arguments);
    },
    /**
     * @override
     */
    _initCommands() {
        this._super();
        this.messaging.update({
            commands: insert({
                channel_types: ['livechat'],
                help: this.env._t("See 15 last visited pages"),
                methodName: 'execute_command_history',
                name: "history",
            }),
        });
    },
});
