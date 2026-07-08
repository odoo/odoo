import { _resolve_messages } from "@mail/../tests/mock_server/mail_mock_server";
import { registerStoreHandler } from "@mail/../tests/mock_server/store_handler";

import { serverState } from "@web/../tests/web_test_helpers";

// Mirrors the store handlers of `mail/controllers/webclient.py` (WebclientController).

registerStoreHandler(
    "mail.thread",
    function store_mail_thread(store, params) {
        store.add(this.env[params.thread_model].browse(params.thread_id), "_store_thread_fields", {
            as_thread: true,
            fields_params: { request_list: params.request_list, chatter_fields: true },
        });
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "init_messaging",
    function store_init_messaging(store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        // is_self is a per-current-user compute only refreshed at create/write in the mock
        DiscussChannelMember.browse(DiscussChannelMember.search([]))._compute_is_self();
        const rtcInvitedChannelIds = DiscussChannelMember._filter([
            ["is_self", "=", true],
            ["rtc_inviting_session_id", "!=", false],
        ]).map((member) => member.channel_id);
        for (const channelId of rtcInvitedChannelIds) {
            store.request_channel_ids.add(channelId);
        }
        if (!ResUsers._is_public(this.env.uid)) {
            const odoobotChatMemberChannelIds = DiscussChannelMember._filter([
                ["partner_id", "=", serverState.odoobotId],
            ]).map((member) => member.channel_id);
            const myMemberChannelIds = DiscussChannelMember._filter([
                ["partner_id", "=", this.env.user.partner_id],
            ]).map((member) => member.channel_id);
            const odoobotChatIds = DiscussChannel.search([
                ["channel_type", "=", "chat"],
                ["id", "in", odoobotChatMemberChannelIds],
                ["id", "in", myMemberChannelIds],
            ]);
            for (const channelId of odoobotChatIds) {
                store.request_channel_ids.add(channelId);
            }
        }
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "res.partner",
    function store_get_res_partner(store, params) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        const [partnerId] = ResPartner.search([["id", "=", params["id"]]]);
        store.add(ResPartner.browse(partnerId), "_store_partner_fields");
    },
    { audience: "everyone" }
);

registerStoreHandler(
    "res.users",
    function store_get_res_users(store, params) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        const [userId] = ResUsers.search([["id", "=", params["id"]]]);
        store.add(ResUsers.browse(userId), "_store_user_fields");
    },
    { audience: "everyone" }
);

registerStoreHandler("mail.activity", function store_get_mail_activity(store, params) {
    /** @type {import("mock_models").MailActivity} */
    const MailActivity = this.env["mail.activity"];
    const activities = MailActivity._filter([["id", "in", params.ids]], { active_test: false });
    store.add(MailActivity.browse(activities.map((a) => a.id)), "_store_activity_fields");
});

registerStoreHandler("failures", function store_get_failures(store) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    /** @type {import("mock_models").MailNotification} */
    const MailNotification = this.env["mail.notification"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];
    if (!this.env.user?.partner_id) {
        return;
    }
    const [partner] = ResPartner.browse(this.env.user.partner_id);
    const messages = MailMessage._filter([
        ["author_id", "=", partner.id],
        ["res_id", "!=", 0],
        ["model", "!=", false],
        ["message_type", "!=", "user_notification"],
    ]).filter((message) => {
        // Purpose is to simulate the following domain on mail.message:
        // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
        // But it's not supported by getRecords domain to follow a relation.
        const notifications = MailNotification._filter([
            ["mail_message_id", "=", message.id],
            ["notification_status", "in", ["bounce", "exception"]],
        ]);
        return notifications.length > 0;
    });
    messages.length = Math.min(messages.length, 100);
    MailMessage._message_notifications_to_store(
        messages.map((message) => message.id),
        store
    );
});

registerStoreHandler(
    "/mail/thread/messages",
    function store_get_thread_messages(store, params) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        store.add_chatter_fields = true;
        const thread = this.env[params.thread_model].browse(params.thread_id);
        const messages = _resolve_messages.call(this, store, {
            ...params.fetch_params,
            domain: [],
            thread,
        });
        if (!ResUsers._is_public(this.env.uid)) {
            MailMessage.set_message_done(messages.map((message) => message.id));
        }
    },
    { audience: "everyone", readonly: false }
);

registerStoreHandler("systray_get_activities", function store_systray_get_activities(store) {
    /** @type {import("mock_models").MailActivity} */
    const MailActivity = this.env["mail.activity"];
    /** @type {import("mock_models").ResUsers} */
    const ResUsers = this.env["res.users"];
    const bus_last_id = this.env["bus.bus"].lastBusNotificationId;
    const groups = ResUsers._get_activity_groups();
    const roleIds = this.env.user.role_ids || [];
    const activities_to_assign_count = roleIds.length
        ? MailActivity._filter([
              ["user_id", "=", false],
              ["role_id", "in", roleIds],
          ]).length
        : 0;
    store.add_global_values({
        activityCounter: groups.reduce((counter, group) => counter + (group.total_count || 0), 0),
        activity_counter_bus_id: bus_last_id,
        activityGroups: groups,
        activities_to_assign_count,
    });
});

registerStoreHandler("mail.canned.response", function store_mail_canned_response(store) {
    const domain = [
        "|",
        ["create_uid", "=", this.env.user.id],
        ["group_ids", "in", this.env.user.group_ids],
    ];
    const CannedResponse = this.env["mail.canned.response"];
    const cannedResponses = CannedResponse.search(domain);
    store.add(CannedResponse.browse(cannedResponses), "_store_canned_response_fields");
});

registerStoreHandler("avatar_card", function store_avatar_card(store, params) {
    const { id, model } = params;
    if (!id || !_get_supported_avatar_card_models().includes(model)) {
        return;
    }
    const Model = this.env[model];
    const [record] = Model.search([["id", "=", id]]);
    if (record) {
        store.add(Model.browse(record), "_store_avatar_card_fields");
    }
});

function _get_supported_avatar_card_models() {
    // not modular but avoids verbose overrides
    return ["res.users", "res.partner", "resource.resource", "hr.employee", "hr.employee.public"];
}
