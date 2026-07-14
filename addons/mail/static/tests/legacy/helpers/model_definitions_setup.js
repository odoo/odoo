/** @odoo-module alias=@mail/../tests/helpers/model_definitions_setup default=false */

import {
    addFakeModel,
    addModelNamesToFetch,
    insertModelFields,
    insertRecords,
} from "@bus/../tests/helpers/model_definitions_helpers";
import { TEST_GROUP_IDS } from "@bus/../tests/helpers/test_constants";

import { Command } from "@mail/../tests/helpers/command";

import { uniqueId } from "@web/core/utils/functions";

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    "mail.activity",
    "mail.activity.type",
    "discuss.channel",
    "discuss.channel.member",
    "discuss.channel.rtc.session",
    "discuss.gif.favorite",
    "discuss.voice.metadata",
    "mail.followers",
    "mail.guest",
    "mail.link.preview",
    "mail.message",
    "mail.message.reaction",
    "mail.message.subtype",
    "mail.notification",
    "mail.canned.response",
    "mail.template",
    "mail.tracking.value",
    "res.users.settings",
    "res.users.settings.volumes",
]);

addFakeModel("res.fake", {
    message_ids: { string: "Messages", type: "one2many", relation: "mail.message" },
    activity_ids: { string: "Activities", type: "one2many", relation: "mail.activity" },
    message_follower_ids: { string: "Followers", type: "one2many", relation: "mail.followers" },
    email_cc: { type: "char" },
    phone: { type: "char" },
    partner_ids: { relation: "res.partner", string: "Related partners", type: "one2many" },
});

addFakeModel("m2x.avatar.user", {
    user_id: { type: "many2one", relation: "res.users" },
    user_ids: { type: "many2many", relation: "res.users", string: "Users" },
});

//--------------------------------------------------------------------------
// Insertion of fields
//--------------------------------------------------------------------------

insertModelFields("mail.activity", {
    chaining_type: { default: "suggest" },
});
insertModelFields("discuss.channel", {
    author_id: {
        default() {
            return this.pyEnv.currentPartnerId;
        },
    },
    avatarCacheKey: { string: "Avatar Cache Key", type: "datetime" },
    channel_member_ids: {
        default() {
            return [
                Command.create({ partner_id: this.pyEnv.currentPartnerId, fold_state: "closed" }),
            ];
        },
    },
    channel_type: { default: "channel" },
    group_public_id: {
        default() {
            return TEST_GROUP_IDS.groupUserId;
        },
    },
    uuid: { default: () => uniqueId("discuss.channel_uuid-") },
});
insertModelFields("res.users", {
    partner_id: {
        default() {
            return this.pyEnv["res.partner"].create({});
        },
    },
});
insertModelFields("mail.activity", {
    user_id: {
        default() {
            return this.pyEnv.currentUserId;
        },
    },
});
insertModelFields("discuss.channel.member", {
    fold_state: { default: "closed" },
    is_pinned: { default: true },
    message_unread_counter: { default: 0 },
});
insertModelFields("mail.message", {
    author_id: {
        default() {
            return this.pyEnv.currentPartnerId;
        },
    },
    pinned_at: { default: () => false },
    is_discussion: { string: "Discussion", type: "boolean" },
    is_note: { string: "Discussion", type: "boolean" },
    needaction_partner_ids: {
        relation: "res.partner",
        string: "Partners with Need Action",
        type: "many2many",
    },
    res_model_name: { string: "Res Model Name", type: "char" },
});
insertModelFields("mail.message.subtype", {
    default: { default: true },
    subtype_xmlid: { type: "char" },
});
insertModelFields("res.users.settings", {
    is_discuss_sidebar_category_channel_open: { default: true },
    is_discuss_sidebar_category_chat_open: { default: true },
});

//--------------------------------------------------------------------------
// Insertion of records
//--------------------------------------------------------------------------

insertRecords("mail.activity.type", [
    { icon: "fa-envelope", id: 1, name: "Email" },
    { icon: "fa-phone", id: 2, name: "Call", category: "phonecall" },
    { icon: "fa-upload", id: 28, name: "Upload Document" },
]);
insertRecords("mail.message.subtype", [
    {
        default: false,
        internal: true,
        name: "Activities",
        sequence: 90,
        subtype_xmlid: "mail.mt_activities",
    },
    {
        default: false,
        internal: true,
        name: "Note",
        sequence: 100,
        subtype_xmlid: "mail.mt_note",
        track_recipients: true,
    },
    { name: "Discussions", sequence: 0, subtype_xmlid: "mail.mt_comment", track_recipients: true },
]);
