/** @odoo-module **/

import { TEST_GROUP_IDS, TEST_USER_IDS } from '@bus/../tests/helpers/test_constants';
import {
    addFakeModel,
    addModelNamesToFetch,
    insertModelFields,
    insertRecords
} from '@bus/../tests/helpers/model_definitions_helpers';

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    'mail.activity', 'mail.activity.type', 'mail.channel', 'mail.channel.member',
    'mail.followers', 'mail.message', 'mail.message.subtype', 'mail.notification',
    'mail.shortcode', 'mail.template', 'mail.tracking.value', 'res.users.settings',
    'res.users.settings.volumes'
]);

addFakeModel('res.fake', {
    message_ids: { string: 'Messages', type: 'one2many', relation: 'mail.message' },
    activity_ids: { string: "Activities", type: 'one2many', relation: 'mail.activity' },
    email_cc: { type: 'char' },
    partner_ids: { relation: 'res.partner', string: "Related partners", type: 'one2many' },
});

addFakeModel('m2x.avatar.user', {
    user_id: { type: 'many2one', relation: 'res.users' },
    user_ids: { type: 'many2many', relation: 'res.users' },
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
            return this.currentPartnerId;
        },
    },
    avatarCacheKey: { string: "Avatar Cache Key", type: "datetime" },
    channel_member_ids: {
        default() {
            return [[0, 0, { partner_id: this.currentPartnerId }]];
        },
    },
    channel_type: { default: 'channel' },
    group_based_subscription: { string: "Group based subscription", type: "boolean" },
    group_public_id: {
        default() {
            return TEST_GROUP_IDS.groupUserId;
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
    author_id: { default: TEST_USER_IDS.currentPartnerId },
    history_partner_ids: { relation: 'res.partner', string: "Partners with History", type: 'many2many' },
    is_discussion: { string: 'Discussion', type: 'boolean' },
    is_note: { string: "Discussion", type: 'boolean' },
    is_notification: { string: "Note", type: 'boolean' },
    needaction_partner_ids: { relation: 'res.partner', string: "Partners with Need Action", type: 'many2many' },
    res_model_name: { string: "Res Model Name", type: 'char' },
});
insertModelFields('mail.message.subtype', {
    subtype_xmlid: { type: 'char' },
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
// Insertion of records
//--------------------------------------------------------------------------

insertRecords('mail.activity.type', [
    { icon: 'fa-envelope', id: 1, name: "Email" },
    { icon: 'fa-upload', id: 28, name: "Upload Document" },
]);
insertRecords('mail.message.subtype', [
    { default: false, internal: true, name: "Activities", sequence: 90, subtype_xmlid: 'mail.mt_activities' },
    {
        default: false, internal: true, name: "Note", sequence: 100, subtype_xmlid: 'mail.mt_note',
        track_recipients: true
    },
    { name: "Discussions", sequence: 0, subtype_xmlid: 'mail.mt_comment', track_recipients: true },
]);
