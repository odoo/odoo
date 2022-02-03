/** @odoo-module **/

import { datetime_to_str } from 'web.time';

export class ModelsInitializer {

    //------------------------------------------------------------------------------
    // Public
    //------------------------------------------------------------------------------

    /**
     * Get the require data for the `startServer` method to work. ie. models, default field values
     * and custom model fields
     */
    static getModelsData() {
        return {
            models: this.getRequiredModels(),
            defaultFieldValues: this.getDefaultFieldValues(),
            customModelFields: this.getCustomFieldsByModel(),
        };
    }

    /**
     * Return the models to be used during the tests as well as their fields. An empty array as
     * their fields means that we will fetch EVERY field present of the server side model
     * definition. Note that since display_name and id are always used, those will be automatically
     * fetched.
     */
    static getRequiredModels() {
        // calendar.event ==> to calendar mock models
        const modelNames = [
            'ir.attachment', 'ir.model', 'mail.activity', 'mail.activity.type', 'mail.followers', 'mail.message.subtype',
            'mail.notification', 'mail.shortcode', 'mail.tracking.value', 'mail.template', 'res.users.settings',
            'res.country', 'calendar.event', 'res.company', 'mail.message', 'res.partner'
        ];
        const models = modelNames.reduce((previous, next) => ({ ...previous, [next]: [] }), {});
        Object.assign(models, {
            'res.partner': [
                'active', 'activity_ids', 'contact_address_complete', 'country_id', 'name',
                'email', 'avatar_128', 'im_status', 'message_follower_ids', 'message_attachment_count',
                'message_ids', 'partner_latitude', 'partner_longitude', 'partner_share',
            ],
            'res.users': ['active', 'im_status', 'partner_id', 'email'],
            'mail.channel': ['channel_type', 'message_unread_counter', 'public', 'uuid'],
        });
        return models;
    }

    /**
     * Return the default field values to apply to the model definitions.
     */
    static getDefaultFieldValues() {
        return {
            'res.users': { active: true },
            'res.partner': { active: true, partner_share: false },
            'res.users.settings': { is_discuss_sidebar_category_channel_open: true, is_discuss_sidebar_category_chat_open: true },
            'mail.activity': {
                chaining_type: 'suggest',
                create_date: () => moment().format('YYYY-MM-DD'),
                date_deadline: () => moment().format('YYYY-MM-DD'),
            },
            'mail.activity.type': { chaining_type: 'suggest', active: true },
            'mail.notification': { is_read: false, notification_status: 'ready', notification_type: 'email' },
            'mail.channel': {
                avatarCacheKey: () => moment.utc().format("YYYYMMDDHHmmss"),
                channel_type: 'channel',
                group_based_subscription: false,
                is_minimized: false,
                is_pinned: true,
                last_interest_dt: () => datetime_to_str(new Date()),
                members: function () { return [this.currentPartnerId]; },
                public: 'groups',
                state: 'open',
                uuid: () => _.uniqueId('mail.channel_uuid-'),
            },
            'mail.message': {
                attachment_ids: [],
                author_id: function () { return this.currentPartnerId; },
                body: '<p></p>',
                date: () => moment.utc().format("YYYY-MM-DD HH:mm:ss"),
                message_type: 'email',
            },
            'mail.message.subtype': {
                default: true,
                sequence: 1,
            },

        };
    }

    /**
     * Return fields that are not present in the server side model definition but are used to ease
     * testing.
     */
    static getCustomFieldsByModel() {
        return {
            'mail.channel': {
                avatarCacheKey: { string: "Avatar Cache Key", type: "datetime" },
                custom_channel_name: { string: "Custom channel name", type: 'char' },
                fetched_message_id: { string: "Last Fetched", type: 'many2one', relation: 'mail.message' },
                group_based_subscription: { string: "Group based subscription", type: "boolean" },
                is_minimized: { string: "isMinimized", type: "boolean" },
                is_pinned: { string: "isPinned", type: "boolean" },
                last_interest_dt: { string: "Last Interest", type: "datetime" },
                members: { string: "Members", type: 'many2many', relation: 'res.partner' },
                seen_message_id: { string: "Last Seen", type: 'many2one', relation: 'mail.message' },
                state: { string: "FoldState", type: "char" },
            },
            'mail.message': {
                history_partner_ids: { string: "Partners with History", type: 'many2many', relation: 'res.partner' },
                is_discussion: { string: "Discussion", type: 'boolean' },
                is_note: { string: "Note", type: 'boolean' },
                is_notification: { string: "Notification", type: 'boolean' },
                needaction_partner_ids: { string: "Partners with Need Action", type: 'many2many', relation: 'res.partner' },
                res_model_name: { string: "Res Model Name", type: 'char' },
            },
            'mail.message.subtype': {
                subtype_xmlid: { type: 'char' },
            },
            'mail.followers': {
                is_editable: { type: 'boolean' },
                partner_id: { type: 'integer' },
            },
            'mail.tracking.value': {
                changed_field: { string: 'Changed field', type: 'char' },
            },
            'res.partner': {
                description: { string: 'description', type: 'text' },
            },
        };
    }
}
