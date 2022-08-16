/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

/**
 * Mirrors the fields of the python model res.users.settings.
 */
registerModel({
    name: 'res.users.settings',
    fields: {
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        is_discuss_sidebar_category_channel_open: attr({
            default: true,
        }),
        is_discuss_sidebar_category_chat_open: attr({
            default: true,
        }),
        push_to_talk_key: attr(),
        use_push_to_talk: attr({
            default: false,
        }),
        user_id: one('User', {
            inverse: 'res_users_settings_id',
            required: true,
        }),
        voice_active_duration: attr(),
        /**
         * States the volume chosen by the current user for each other user.
         */
        volume_settings_ids: many('res.users.settings.volumes', {
            inverse: 'user_setting_id',
            isCausal: true,
        }),
    },
});
