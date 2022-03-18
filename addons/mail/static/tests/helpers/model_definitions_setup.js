/** @odoo-module **/

import { TEST_USER_IDS } from '@mail/utils/test_utils';
import {
    addFakeModel,
    addModelNamesToFetch,
    insertModelFields,
    insertRecords
} from '@mail/../tests/helpers/model_definitions_helpers';

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    'ir.attachment', 'ir.model', 'ir.model.fields', 'mail.activity', 'mail.activity.type',
    'mail.channel', 'mail.followers', 'mail.message', 'mail.message.subtype',
    'mail.notification', 'mail.shortcode', 'mail.template', 'mail.tracking.value',
    'res.company', 'res.country', 'res.partner', 'res.users', 'res.users.settings',
]);

addFakeModel('res.fake', {
    activity_ids: { string: "Activities", type: 'one2many', relation: 'mail.activity' },
    email_cc: { type: 'char' },
    partner_ids: { relation: 'res.partner', string: "Related partners", type: 'many2one', },
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
    custom_channel_name: { string: "Custom channel name", type: 'char' },
    fetched_message_id: { relation: 'mail.message', string: "Last Fetched", type: 'many2one' },
    group_based_subscription: { string: "Group based subscription", type: "boolean" },
    is_minimized: { string: "isMinimized", type: "boolean" },
    is_pinned: { default: true, string: "isPinned", type: "boolean" },
    last_interest_dt: { string: "Last Interest", type: "datetime" },
    members: {
        default() {
            return [this.currentPartnerId];
        },
        relation: 'res.partner',
        string: "Members",
        type: 'many2many'
    },
    message_unread_counter: { string: 'Unread counter', type: 'integer' },
    seen_message_id:  { relation: 'mail.message', string: "Last Seen", type: 'many2one' },
    state: { default: 'open', string: "FoldState", type: "char" },
    uuid: { default: () => _.uniqueId('mail.channel_uuid-') },
});
insertModelFields('mail.followers', {
    is_editable: { type: 'boolean' },
});
insertModelFields('mail.message', {
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
insertModelFields('res.partner', {
    description: { string: 'description', type: 'text' },
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
    { default: false, internal: true, name: "Note", sequence: 100, subtype_xmlid: 'mail.mt_note' },
    { name: "Discussions", sequence: 0, subtype_xmlid: 'mail.mt_comment' },
]);
insertRecords('res.company', [{ id: 1 }]);
insertRecords('res.users', [
    { display_name: "Your Company, Mitchell Admin", id: TEST_USER_IDS.currentUserId, name: "Mitchell Admin", partner_id: TEST_USER_IDS.currentPartnerId, },
    { active: false, display_name: "Public user", id: TEST_USER_IDS.publicUserId, name: "Public user", partner_id: TEST_USER_IDS.publicPartnerId, },
]);
insertRecords('res.partner', [
    { active: false, display_name: "Public user", id: TEST_USER_IDS.publicPartnerId, },
    { display_name: "Your Company, Mitchell Admin", id: TEST_USER_IDS.currentPartnerId, name: "Mitchell Admin", },
    { active: false, display_name: "OdooBot", id: TEST_USER_IDS.partnerRootId, },
]);
