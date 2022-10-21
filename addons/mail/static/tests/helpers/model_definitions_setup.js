/** @odoo-module **/

import {
    addFakeModel,
    addModelNamesToFetch,
    addRefsToFetch,
    insertModelFields,
} from '@bus/../tests/helpers/model_definitions_helpers';

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    'mail.activity', 'mail.activity.type', 'mail.channel', 'mail.channel.member',
    'mail.channel.rtc.session', 'mail.followers', 'mail.guest', 'mail.link.preview', 'mail.message',
    'mail.message.subtype', 'mail.notification', 'mail.shortcode', 'mail.template',
    'mail.tracking.value', 'res.users.settings', 'res.users.settings.volumes'
]);

addFakeModel('res.fake', {
    message_ids: { string: 'Messages', type: 'one2many', relation: 'mail.message' },
    activity_ids: { string: "Activities", type: 'one2many', relation: 'mail.activity' },
    email_cc: { type: 'char' },
    partner_ids: { relation: 'res.partner', string: "Related partners", type: 'one2many' },
});

addFakeModel('m2x.avatar.user', {
    user_id: { type: 'many2one', relation: 'res.users' },
    user_ids: { type: 'many2many', relation: 'res.users', string: 'Users'},
});

//--------------------------------------------------------------------------
// Insertion of fields
//--------------------------------------------------------------------------

insertModelFields('mail.activity', {
    chaining_type: { default: 'suggest' },
});
insertModelFields('mail.channel', {
    author_id: {
        default() {
            return this.pyEnv.currentPartnerId;
        },
    },
    avatarCacheKey: { string: "Avatar Cache Key", type: "datetime" },
    channel_member_ids: {
        default() {
            return [[0, 0, { partner_id: this.pyEnv.currentPartnerId }]];
        },
    },
    channel_type: { default: 'channel' },
    group_based_subscription: { string: "Group based subscription", type: "boolean" },
    group_public_id: {
        default() {
            return this.pyEnv.ref('base.group_public').id;
        },
    },
    uuid: { default: () => _.uniqueId('mail.channel_uuid-') },
});
insertModelFields('mail.channel.member', {
    fold_state: { default: 'open' },
    is_pinned: { default: true },
    message_unread_counter: { default: 0 },
});
insertModelFields('mail.message', {
    author_id: {
        default() {
            return this.pyEnv.currentPartnerId;
        },
    },
    history_partner_ids: { relation: 'res.partner', string: "Partners with History", type: 'many2many' },
    is_discussion: { string: 'Discussion', type: 'boolean' },
    is_note: { string: "Discussion", type: 'boolean' },
    is_notification: { string: "Note", type: 'boolean' },
    needaction_partner_ids: { relation: 'res.partner', string: "Partners with Need Action", type: 'many2many' },
    res_model_name: { string: "Res Model Name", type: 'char' },
});
insertModelFields('mail.tracking.value', {
    changed_field: { string: 'Changed field', type: 'char' },
    new_value: { string: 'New value', type: 'char' },
    old_value: { string: 'Old value', type: 'char' },
});
insertModelFields('res.users.settings', {
    is_discuss_sidebar_category_channel_open: { default: true },
    is_discuss_sidebar_category_chat_open: { default: true },
});

//--------------------------------------------------------------------------
// Records to fetch
//--------------------------------------------------------------------------

addRefsToFetch([
    'mail.mail_activity_data_email', 'mail.mail_activity_data_upload_document',
    'mail.mt_comment', 'mail.mt_note', 'mail.mt_activities',
]);
