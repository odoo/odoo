/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'im_livechat/static/tests/helpers/models_initializer.js', {
    /**
     * @override
     */
    getRequiredModels() {
        const models = this._super(...arguments);
        models['im_livechat.channel'] = ['user_ids'];
        models['mail.channel'].push('country_id', 'livechat_active', 'livechat_channel_id', 'livechat_operator_id');
        models['res.users'].push('livechat_username');
        return models;
    },
    /**
     * @override
     */
    getDefaultFieldValues() {
        const defaultFieldValues = this._super(...arguments);
        defaultFieldValues['mail.channel'].livechat_active = false;
        defaultFieldValues['res.users.settings'].is_discuss_sidebar_category_livechat_open = true;
        return defaultFieldValues;
    },
    /**
     * @override
     */
    getCustomFieldsByModel() {
        const customFieldsByModel = this._super(...arguments);
        Object.assign(customFieldsByModel['mail.channel'], {
            anonymous_name: { string: "Anonymous Name", type: 'char' },
        });
        return customFieldsByModel;
    }
});
