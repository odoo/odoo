import {
    authenticate,
    getKwArgs,
    logout,
    makeKwArgs,
    MockServer,
    MockServerError,
    models,
    onRpc,
    serverState,
    unmakeKwArgs,
} from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { groupBy } from "@web/core/utils/arrays";

const mockRpcRegistry = registry.category("mail.mock_rpc");
export const DISCUSS_ACTION_ID = 104;

/**
 * @template [T={}]
 * @typedef {import("@web/../tests/web_test_helpers").RouteCallback<T>} RouteCallback
 */

const { DateTime } = luxon;

/** @param {import("./mock_model").MailGuest} guest */
export const authenticateGuest = (guest) => {
    const { env } = MockServer;
    /** @type {import("mock_models").ResUsers} */
    const ResUsers = env["res.users"];
    if (!guest?.id) {
        throw new MockServerError("Unauthorized");
    }
    const [publicUser] = ResUsers.read(serverState.publicUserId);
    env.cookie.set("dgid", guest.id);
    authenticate(publicUser.login, publicUser.password);
    env.uid = serverState.publicUserId;
};

/**
 * Executes the given callback as the given guest, then restores the previous user.
 *
 * @param {number} guestId
 * @param {() => any} fn
 */
export async function withGuest(guestId, fn) {
    const { env } = MockServer;
    /** @type {import("mock_models").MailGuest} */
    const MailGuest = env["mail.guest"];
    const currentUser = env.user;
    const [targetGuest] = MailGuest.browse(guestId);
    authenticateGuest(targetGuest);
    let result;
    try {
        result = await fn();
    } finally {
        if (currentUser) {
            authenticate(currentUser.login, currentUser.password);
        } else {
            logout();
            env.cookie.delete("dgid");
        }
    }
    return result;
}

/** @param {Request} request */
export const parseRequestParams = async (request) => {
    const response = await request.json();
    return response.params;
};

const onRpcBeforeGlobal = { cb: (route, args) => {} };
const onRpcAfterGlobal = { cb: (route, args) => {} };
// using a registry category to not expose for manual import
// We should use `onRpcBefore`/`onRpcAfter` with 1st parameter being (route, args) callback function
registry.category("mail.on_rpc_before_global").add(true, onRpcBeforeGlobal);
registry.category("mail.on_rpc_after_global").add(true, onRpcAfterGlobal);
export function registerRoute(route, handler) {
    async function beforeCallableHandler(request) {
        let args;
        try {
            args = await parseRequestParams(request);
        } catch {
            args = await request.text();
        }
        let res = await onRpcBeforeGlobal.cb?.(route, args);
        if (res !== undefined) {
            return res;
        }
        res = await beforeCallableHandler.before?.(args);
        if (res !== undefined) {
            return res;
        }
        const response = handler.call(this, request);
        res = await beforeCallableHandler.after?.(response);
        if (res !== undefined) {
            return res;
        }
        return response;
    }
    mockRpcRegistry.add(route, beforeCallableHandler);
    onRpc(route, beforeCallableHandler);
}

// RPC handlers

registerRoute("/mail/attachment/upload", mail_attachment_upload);
/** @type {RouteCallback}} */
async function mail_attachment_upload(request) {
    /** @type {import("mock_models").DiscussVoiceMetadata} */
    const DiscussVoiceMetadata = this.env["discuss.voice.metadata"];
    /** @type {import("mock_models").IrAttachment} */
    const IrAttachment = this.env["ir.attachment"];

    const body = await request.text();
    const ufile = body.get("ufile");
    const is_pending = body.get("is_pending") === "true";
    const model = is_pending ? "mail.compose.message" : body.get("thread_model");
    const id = is_pending ? 0 : parseInt(body.get("thread_id"));
    const attachmentId = IrAttachment.create({
        // datas,
        mimetype: ufile.type,
        name: ufile.name,
        res_id: id,
        res_model: model,
    });
    if (body.get("voice")) {
        DiscussVoiceMetadata.create({ attachment_id: attachmentId });
    }
    return {
        data: new mailDataHelpers.Store(IrAttachment.browse(attachmentId)).get_result(),
    };
}

registerRoute("/mail/attachment/delete", mail_attachment_delete);
/** @type {RouteCallback} */
async function mail_attachment_delete(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").IrAttachment} */
    const IrAttachment = this.env["ir.attachment"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { attachment_id } = await parseRequestParams(request);
    const [partner] = ResPartner.read(this.env.user.partner_id);
    BusBus._sendone(partner, "ir.attachment/delete", {
        id: attachment_id,
    });
    return IrAttachment.unlink([attachment_id]);
}

registerRoute("/discuss/channel/attachments", load_attachments);
/** @type {RouteCallback} */
async function load_attachments(request) {
    /** @type {import("mock_models").IrAttachment} */
    const IrAttachment = this.env["ir.attachment"];

    const {
        channel_id,
        limit = 30,
        older_attachment_id = null,
    } = await parseRequestParams(request);
    const attachmentIds = IrAttachment.filter(
        ({ id, res_id, res_model }) =>
            res_id === channel_id &&
            res_model === "discuss.channel" &&
            (!older_attachment_id || id < older_attachment_id)
    )
        .sort()
        .slice(0, limit)
        .map(({ id }) => id);
    return new mailDataHelpers.Store(IrAttachment.browse(attachmentIds)).get_result();
}

registerRoute("/mail/rtc/channel/join_call", channel_call_join);
/** @type {RouteCallback} */
async function channel_call_join(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").DiscussChannelRtcSession} */
    const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];

    const { channel_id } = await parseRequestParams(request);
    const memberOfCurrentUser = DiscussChannel._find_or_create_member_for_self(channel_id);
    const sessionId = DiscussChannelRtcSession.create({
        channel_member_id: memberOfCurrentUser.id,
        channel_id, // on the server, this is a related field from channel_member_id and not explicitly set
        guest_id: memberOfCurrentUser.guest_id,
        partner_id: memberOfCurrentUser.partner_id,
    });
    const channelMembers = DiscussChannelMember._filter([["channel_id", "=", channel_id]]);
    const rtcSessions = DiscussChannelRtcSession._filter([
        ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
    ]);
    return new mailDataHelpers.Store(DiscussChannel.browse(channel_id), {
        rtcSessions: mailDataHelpers.Store.many(rtcSessions, "ADD"),
    })
        .add("Rtc", {
            iceServers: false,
            localSession: mailDataHelpers.Store.one(DiscussChannelRtcSession.browse(sessionId)),
        })
        .get_result();
}

registerRoute("/mail/rtc/channel/leave_call", channel_call_leave);
/** @type {RouteCallback} */
async function channel_call_leave(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").DiscussChannelRtcSession} */
    const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];
    /** @type {import("mock_models").MailGuest} */
    const MailGuest = this.env["mail.guest"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { channel_id } = await parseRequestParams(request);
    const channelMembers = DiscussChannelMember._filter([["channel_id", "=", channel_id]]);
    const rtcSessions = DiscussChannelRtcSession._filter([
        ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
    ]);
    const notifications = [];
    const sessionsByChannelId = {};
    for (const session of rtcSessions) {
        const [member] = DiscussChannelMember.browse(session.channel_member_id);
        if (!sessionsByChannelId[member.channel_id]) {
            sessionsByChannelId[member.channel_id] = [];
        }
        sessionsByChannelId[member.channel_id].push(session);
    }
    for (const [channelId, sessions] of Object.entries(sessionsByChannelId)) {
        const channel = DiscussChannel.search_read([["id", "=", parseInt(channelId)]])[0];
        notifications.push([
            channel,
            "mail.record/insert",
            new mailDataHelpers.Store(DiscussChannel.browse(Number(channelId)), {
                rtcSessions: mailDataHelpers.Store.many(
                    DiscussChannelRtcSession.browse(sessions.map((session) => session.id)),
                    "DELETE",
                    makeKwArgs({ only_id: true })
                ),
            }).get_result(),
        ]);
    }
    for (const rtcSession of rtcSessions) {
        const target = rtcSession.guest_id
            ? MailGuest.search_read([["id", "=", rtcSession.guest_id]])[0]
            : ResPartner.search_read([["id", "=", rtcSession.partner_id]])[0];
        notifications.push([
            target,
            "discuss.channel.rtc.session/ended",
            { sessionId: rtcSession.id },
        ]);
    }
    BusBus._sendmany(notifications);
}

registerRoute("/discuss/channel/get_or_create_chat", discuss_get_or_create_chat);
/** @type {RouteCallback} */
async function discuss_get_or_create_chat(request) {
    const { partners_to } = await parseRequestParams(request);

    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    const channel = DiscussChannel._get_or_create_chat(partners_to);
    return {
        channel_id: channel.id,
        data: new mailDataHelpers.Store(DiscussChannel.browse(channel.id)).get_result(),
    };
}

registerRoute("/discuss/channel/create_channel", discuss_create_channel);
/** @type {RouteCallback} */
async function discuss_create_channel(request) {
    const { name, group_id } = await parseRequestParams(request);

    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    return DiscussChannel._create_channel(name, group_id);
}

registerRoute("/discuss/channel/create_group", discuss_create_group);
/** @type {RouteCallback} */
async function discuss_create_group(request) {
    const kwargs = await parseRequestParams(request);
    const partners_to = kwargs.partners_to || [];
    const name = kwargs.name || "";

    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    return DiscussChannel._create_group(partners_to, name);
}

registerRoute("/discuss/channel/members", discuss_channel_members);
/** @type {RouteCallback} */
async function discuss_channel_members(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id, known_member_ids } = await parseRequestParams(request);
    return DiscussChannel._load_more_members([channel_id], known_member_ids);
}

registerRoute("/discuss/channel/messages", discuss_channel_messages);
/** @type {RouteCallback} */
async function discuss_channel_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { channel_id, fetch_params = {} } = await parseRequestParams(request);
    const domain = [
        ["res_id", "=", channel_id],
        ["model", "=", "discuss.channel"],
        ["message_type", "!=", "user_notification"],
    ];
    const res = MailMessage._message_fetch(domain, makeKwArgs(fetch_params));
    const { messages } = res;
    delete res.messages;
    if (!fetch_params.around) {
        MailMessage.set_message_done(messages.map((message) => message.id));
    }
    return {
        ...res,
        data: new mailDataHelpers.Store(
            MailMessage.browse(messages.map((message) => message.id)),
            makeKwArgs({ for_current_user: true })
        ).get_result(),
        messages: mailDataHelpers.Store.many_ids(messages),
    };
}

registerRoute("/discuss/channel/sub_channel/create", discuss_channel_sub_channel_create);
async function discuss_channel_sub_channel_create(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    const { from_message_id, parent_channel_id, name } = await parseRequestParams(request);
    return DiscussChannel._create_sub_channel(
        [parent_channel_id],
        makeKwArgs({ from_message_id, name })
    );
}

registerRoute("/discuss/channel/sub_channel/fetch", discuss_channel_sub_channel_fetch);
async function discuss_channel_sub_channel_fetch(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    const { parent_channel_id, before, limit } = await parseRequestParams(request);
    const domain = [["parent_channel_id", "=", parent_channel_id]];
    if (before) {
        domain.push(["id", "<", before]);
    }
    const subChannels = DiscussChannel.search(domain, makeKwArgs({ limit, order: "id DESC" }));
    const store = new mailDataHelpers.Store(subChannels);
    const lastMessageIds = [];
    for (const channel of subChannels) {
        const lastMessageId = Math.max(channel.message_ids);
        if (lastMessageId) {
            lastMessageIds.push(lastMessageId);
        }
    }
    store.add(MailMessage.browse(lastMessageIds));
    return store.get_result();
}

registerRoute("/discuss/settings/mute", discuss_settings_mute);
/** @type {RouteCallback} */
async function discuss_settings_mute(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").ResUsersSettings} */
    const ResUsersSettings = this.env["res.users.settings"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { channel_id, minutes } = await parseRequestParams(request);
    let mute_until_dt;
    if (minutes === -1) {
        mute_until_dt = serializeDateTime(DateTime.fromISO("9999-12-31T23:59:59"));
    } else if (minutes) {
        mute_until_dt = serializeDateTime(DateTime.now().plus({ minutes }));
    } else {
        mute_until_dt = false;
    }
    if (channel_id) {
        const member = DiscussChannel._find_or_create_member_for_self(channel_id);
        DiscussChannelMember.write([member.id], { mute_until_dt });
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(
            partner,
            "mail.record/insert",
            new mailDataHelpers.Store(DiscussChannel.browse(member.channel_id), {
                mute_until_dt,
            }).get_result()
        );
    } else {
        const settings = ResUsersSettings._find_or_create_for_user(this.env.user.id);
        ResUsersSettings.set_res_users_settings(settings.id, { mute_until_dt });
    }
    return "dummy";
}

registerRoute("/discuss/channel/notify_typing", discuss_channel_notify_typing);
/** @type {RouteCallback} */
async function discuss_channel_notify_typing(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];

    const { channel_id, is_typing } = await parseRequestParams(request);
    const memberOfCurrentUser = DiscussChannel._find_or_create_member_for_self(channel_id);
    if (!memberOfCurrentUser) {
        return;
    }
    DiscussChannelMember.notify_typing([memberOfCurrentUser.id], is_typing);
}

registerRoute("/discuss/channel/ping", channel_ping);
/** @type {RouteCallback} */
async function channel_ping(request) {}

registerRoute("/discuss/channel/pinned_messages", discuss_channel_pins);
/** @type {RouteCallback} */
async function discuss_channel_pins(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { channel_id } = await parseRequestParams(request);
    const messageIds = MailMessage.search([
        ["model", "=", "discuss.channel"],
        ["res_id", "=", channel_id],
        ["pinned_at", "!=", false],
    ]);
    return new mailDataHelpers.Store(
        messageIds,
        makeKwArgs({ for_current_user: true })
    ).get_result();
}

registerRoute("/discuss/channel/mark_as_read", discuss_channel_mark_as_read);
/** @type {RouteCallback} */
async function discuss_channel_mark_as_read(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    const { channel_id, last_message_id } = await parseRequestParams(request);
    const [partner, guest] = this.env["res.partner"]._get_current_persona();
    const [memberId] = this.env["discuss.channel.member"].search([
        ["channel_id", "=", channel_id],
        partner ? ["partner_id", "=", partner.id] : ["guest_id", "=", guest.id],
    ]);
    if (!memberId) {
        return; // ignore if the member left in the meantime
    }
    return DiscussChannelMember._mark_as_read([memberId], last_message_id);
}

registerRoute(
    "/discuss/channel/set_new_message_separator",
    discuss_channel_set_new_message_separator
);
/** @type {RouteCallback} */
async function discuss_channel_set_new_message_separator(request) {
    const { channel_id, message_id } = await parseRequestParams(request);
    const [partner, guest] = this.env["res.partner"]._get_current_persona();
    const [memberId] = this.env["discuss.channel.member"].search([
        ["channel_id", "=", channel_id],
        partner ? ["partner_id", "=", partner.id] : ["guest_id", "=", guest.id],
    ]);
    return this.env["discuss.channel.member"]._set_new_message_separator(
        [memberId],
        message_id,
        true
    );
}

registerRoute("/discuss/gif/favorites", get_favorites);
/** @type {RouteCallback} */
async function get_favorites(request) {
    return [[]];
}

registerRoute("/mail/history/messages", discuss_history_messages);
/** @type {RouteCallback} */
async function discuss_history_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    /** @type {import("mock_models").MailNotification} */
    const MailNotification = this.env["mail.notification"];

    const { fetch_params = {} } = await parseRequestParams(request);
    const domain = [["needaction", "=", false]];
    const res = MailMessage._message_fetch(domain, makeKwArgs(fetch_params));
    const { messages } = res;
    delete res.messages;
    const messagesWithNotification = messages.filter((message) => {
        const notifs = MailNotification.search_read([
            ["mail_message_id", "=", message.id],
            ["is_read", "=", true],
            ["res_partner_id", "=", this.env.user.partner_id],
        ]);
        return notifs.length > 0;
    });
    return {
        ...res,
        data: new mailDataHelpers.Store(
            MailMessage.browse(messagesWithNotification.map((message) => message.id)),
            makeKwArgs({ for_current_user: true })
        ).get_result(),
        messages: mailDataHelpers.Store.many_ids(messages),
    };
}

registerRoute("/mail/inbox/messages", discuss_inbox_messages);
/** @type {RouteCallback} */
async function discuss_inbox_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { fetch_params = {} } = await parseRequestParams(request);
    const domain = [["needaction", "=", true]];
    const res = MailMessage._message_fetch(domain, makeKwArgs(fetch_params));
    const { messages } = res;
    delete res.messages;
    return {
        ...res,
        data: new mailDataHelpers.Store(
            MailMessage.browse(messages.map((message) => message.id)),
            makeKwArgs({ for_current_user: true, add_followers: true })
        ).get_result(),
        messages: mailDataHelpers.Store.many_ids(messages),
    };
}

registerRoute("/mail/link_preview", mail_link_preview);
/** @type {RouteCallback} */
async function mail_link_preview(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").MailLinkPreview} */
    const MailLinkPreview = this.env["mail.link.preview"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { message_id } = await parseRequestParams(request);
    const [message] = MailMessage.search_read([["id", "=", message_id]]);
    if (message.body.includes("https://make-link-preview.com")) {
        const linkPreviewId = MailLinkPreview.create({
            message_id: message.id,
            og_description: "test description",
            og_title: "Article title",
            og_type: "article",
            source_url: "https://make-link-preview.com",
        });
        BusBus._sendone(
            MailMessage._bus_notification_target(message_id),
            "mail.record/insert",
            new mailDataHelpers.Store(MailLinkPreview.browse(linkPreviewId)).get_result()
        );
    }
}

registerRoute("/mail/link_preview/hide", mail_link_preview_hide);
/** @type {RouteCallback} */
async function mail_link_preview_hide(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").MailLinkPreview} */
    const MailLinkPreview = this.env["mail.link.preview"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { link_preview_ids } = await parseRequestParams(request);
    for (const linkPreview of MailLinkPreview.browse(link_preview_ids)) {
        BusBus._sendone(
            MailMessage._bus_notification_target(linkPreview.message_id),
            "mail.record/insert",
            new mailDataHelpers.Store(MailMessage.browse(linkPreview.message_id), {
                link_preview_ids: mailDataHelpers.Store.many(
                    MailLinkPreview.browse(linkPreview.id),
                    "DELETE",
                    makeKwArgs({ only_id: true })
                ),
            }).get_result()
        );
    }
    return { link_preview_ids };
}

registerRoute("/mail/message/post", mail_message_post);
/** @type {RouteCallback} */
export async function mail_message_post(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    /** @type {import("mock_models").MailThread} */
    const MailThread = this.env["mail.thread"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { context, post_data, thread_id, thread_model, partner_emails, canned_response_ids } =
        await parseRequestParams(request);
    if (canned_response_ids) {
        for (const cannedResponseId of canned_response_ids) {
            this.env["mail.canned.response"].write([cannedResponseId], {
                last_used: serializeDateTime(DateTime.now()),
            });
        }
    }
    if (partner_emails) {
        post_data.partner_ids = post_data.partner_ids || [];
        for (const email of partner_emails) {
            const partner = ResPartner._filter([["email", "=", email]]);
            if (partner.length !== 0) {
                post_data.partner_ids.push(partner[0].id);
            } else {
                const partner_id = ResPartner.create({
                    email,
                    name: email,
                });
                post_data.partner_ids.push(partner_id);
            }
        }
    }
    const finalData = {};
    const allowedParams = [
        "attachment_ids",
        "body",
        "message_type",
        "partner_ids",
        "subtype_xmlid",
    ];
    if (thread_model === "discuss.channel") {
        allowedParams.push("parent_id", "special_mentions");
    }
    for (const allowedParam of allowedParams) {
        if (post_data[allowedParam] !== undefined) {
            finalData[allowedParam] = post_data[allowedParam];
        }
    }
    const kwargs = makeKwArgs({ ...finalData, context });
    let messageIds;
    if (thread_model === "discuss.channel") {
        messageIds = DiscussChannel.message_post(thread_id, kwargs);
    } else {
        const model = this.env[thread_model];
        messageIds = MailThread.message_post.call(model, [thread_id], {
            ...kwargs,
            model: thread_model,
        });
    }
    return new mailDataHelpers.Store(
        MailMessage.browse(messageIds[0]),
        makeKwArgs({ for_current_user: true })
    ).get_result();
}

registerRoute("/mail/message/reaction", mail_message_reaction);
/** @type {RouteCallback} */
async function mail_message_reaction(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    const { action, content, message_id } = await parseRequestParams(request);
    const partner_id = this.env.user?.partner_id ?? false;
    const guest_id = this.env.cookie.get("dgid") ?? false;
    const store = new mailDataHelpers.Store();
    MailMessage._message_reaction(message_id, content, partner_id, guest_id, action, store);
    return store.get_result();
}

registerRoute("/mail/message/translate", translate);
/** @type {RouteCallback} */
async function translate(request) {}

registerRoute("/mail/message/update_content", mail_message_update_content);
/** @type {RouteCallback} */
async function mail_message_update_content(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").IrAttachment} */
    const IrAttachment = this.env["ir.attachment"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { attachment_ids, body, message_id } = await parseRequestParams(request);
    const [message] = MailMessage.browse(message_id);
    const msg_values = {};
    if (body !== null) {
        const edit_label = "<span class='o-mail-Message-edited'/>";
        msg_values.body = body === "" && attachment_ids.length === 0 ? "" : body + edit_label;
    }
    if (attachment_ids.length === 0) {
        IrAttachment.unlink(message.attachment_ids);
    } else {
        const attachments = IrAttachment.browse(attachment_ids).filter(
            (attachment) =>
                attachment.res_model === "mail.compose.message" &&
                attachment.create_uid === this.env.user?.id
        );
        IrAttachment.write(
            attachments.map((attachment) => attachment.id),
            {
                model: message.model,
                res_id: message.res_id,
            }
        );
        msg_values.attachment_ids = attachment_ids;
    }
    if (!body && attachment_ids.length === 0) {
        msg_values.partner_ids = false;
        msg_values.parent_id = false;
    }
    MailMessage.write([message_id], msg_values);
    BusBus._sendone(
        MailMessage._bus_notification_target(message.id),
        "mail.record/insert",
        new mailDataHelpers.Store(MailMessage.browse(message.id), {
            attachment_ids: mailDataHelpers.Store.many(IrAttachment.browse(message.attachment_ids)),
            body: message.body,
            pinned_at: message.pinned_at,
            recipients: mailDataHelpers.Store.many(
                this.env["res.partner"].browse(message.partner_ids),
                makeKwArgs({ fields: ["avatar_128", "name"] })
            ),
            parentMessage: mailDataHelpers.Store.one(MailMessage.browse(message.parent_id)),
        }).get_result()
    );
    return new mailDataHelpers.Store(
        MailMessage.browse(message_id),
        makeKwArgs({ for_current_user: true })
    ).get_result();
}

registerRoute("/discuss/channel/<int:cid>/partner/<int:pid>/avatar_128", partnerAvatar128);
/** @type {RouteCallback} */
async function partnerAvatar128(request, { cid, pid }) {
    return [cid, pid];
}

registerRoute("/mail/partner/from_email", mail_thread_partner_from_email);
/** @type {RouteCallback} */
async function mail_thread_partner_from_email(request) {
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { thread_model, thread_id, emails } = await parseRequestParams(request);
    // use variables, but don't actually implement py in JS, much effort for nothing
    this.env[thread_model].browse(thread_id);
    const partners = emails.map((email) => ResPartner.search([["email", "=", email]])[0]);
    for (const index in partners) {
        if (!partners[index]) {
            const email = emails[index];
            partners[index] = ResPartner.create({
                email,
                name: email,
            });
        }
    }
    return partners.map((partner_id) => {
        const [partner] = ResPartner.browse(partner_id);
        return { id: partner_id, name: partner.name, email: partner.email };
    });
}

registerRoute("/mail/read_subscription_data", read_subscription_data);
/** @type {RouteCallback} */
async function read_subscription_data(request) {
    /** @type {import("mock_models").MailFollowers} */
    const MailFollowers = this.env["mail.followers"];
    /** @type {import("mock_models").MailMessageSubtype} */
    const MailMessageSubtype = this.env["mail.message.subtype"];

    const { follower_id } = await parseRequestParams(request);
    const [follower] = MailFollowers.browse(follower_id);
    const subtypes = MailMessageSubtype._filter([
        "&",
        ["hidden", "=", false],
        "|",
        ["res_model", "=", follower.res_model],
        ["res_model", "=", false],
    ]);
    const subtypes_list = subtypes.map((subtype) => {
        const [parent] = MailMessageSubtype.browse(subtype.parent_id);
        return {
            default: subtype.default,
            followed: follower.subtype_ids.includes(subtype.id),
            id: subtype.id,
            internal: subtype.internal,
            name: subtype.name,
            parent_model: parent ? parent.res_model : false,
            res_model: subtype.res_model,
            sequence: subtype.sequence,
        };
    });
    // NOTE: server is also doing a sort here, not reproduced for simplicity
    return subtypes_list;
}

registerRoute("/mail/rtc/session/update_and_broadcast", session_update_and_broadcast);
/** @type {RouteCallback} */
async function session_update_and_broadcast(request) {
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").DiscussChannelRtcSession} */
    const DiscussChannelRtcSession = this.env["discuss.channel.rtc.session"];

    const { session_id, values } = await parseRequestParams(request);
    const [session] = DiscussChannelRtcSession.search_read([["id", "=", session_id]]);
    const [currentChannelMember] = DiscussChannelMember.search_read([
        ["id", "=", session.channel_member_id[0]],
    ]);
    if (session && currentChannelMember.partner_id[0] === serverState.partnerId) {
        DiscussChannelRtcSession._update_and_broadcast(session.id, values);
    }
}

registerRoute("/mail/starred/messages", discuss_starred_messages);
/** @type {RouteCallback} */
async function discuss_starred_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { fetch_params = {} } = await parseRequestParams(request);
    const domain = [["starred_partner_ids", "in", [this.env.user.partner_id]]];
    const res = MailMessage._message_fetch(domain, makeKwArgs(fetch_params));
    const { messages } = res;
    delete res.messages;
    return {
        ...res,
        data: new mailDataHelpers.Store(
            MailMessage.browse(messages.map((message) => message.id)),
            makeKwArgs({ for_current_user: true })
        ).get_result(),
        messages: mailDataHelpers.Store.many_ids(messages),
    };
}

registerRoute("/mail/thread/messages", mail_thread_messages);
/** @type {RouteCallback} */
async function mail_thread_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { fetch_params = {}, thread_id, thread_model } = await parseRequestParams(request);
    const domain = [
        ["res_id", "=", thread_id],
        ["model", "=", thread_model],
        ["message_type", "!=", "user_notification"],
    ];
    const res = MailMessage._message_fetch(domain, makeKwArgs(fetch_params));
    const { messages } = res;
    delete res.messages;
    MailMessage.set_message_done(messages.map((message) => message.id));
    return {
        ...res,
        data: new mailDataHelpers.Store(
            MailMessage.browse(messages.map((message) => message.id)),
            makeKwArgs({ for_current_user: true })
        ).get_result(),
        messages: mailDataHelpers.Store.many_ids(messages),
    };
}

registerRoute("/mail/thread/recipients/fields", mail_thread_recipients_fields);
async function mail_thread_recipients_fields(request) {
    return {
        partner_fields: [],
        primary_email_field: [],
    };
}

registerRoute("mail/thread/update_suggested_recipents", mail_thread_update_suggested_recipients);
async function mail_thread_update_suggested_recipients(request) {
    return [];
}

registerRoute("/mail/action", mail_action);
/** @type {RouteCallback} */
async function mail_action(request) {
    return (await processRequest.call(this, request)).get_result();
}

registerRoute("/mail/data", mail_data);
/** @type {RouteCallback} */
export async function mail_data(request) {
    return (await processRequest.call(this, request)).get_result();
}

registerRoute("/discuss/search", search);
/** @type {RouteCallback} */
async function search(request) {
    const { term, limit = 8 } = await parseRequestParams(request);

    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const store = new mailDataHelpers.Store();
    const base_domain = [
        ["name", "ilike", term],
        ["channel_type", "!=", "chat"],
    ];
    const priority_conditions = [[["is_member", "=", true], ...base_domain], base_domain];
    const channels = new Set();
    let remaining_limit;
    for (const domain of priority_conditions) {
        remaining_limit = limit - channels.size;
        if (remaining_limit <= 0) {
            break;
        }
        const channelIds = DiscussChannel.search(
            Domain.and([[["id", "not in", [...channels]]], domain]).toList(),
            undefined,
            remaining_limit
        );
        for (const channelId of channelIds) {
            channels.add(channelId);
        }
    }
    store.add(channels);
    ResPartner._search_for_channel_invite(store, term, undefined, limit);
    return store.get_result();
}

registerRoute("/mail/thread/recipients/get_suggested_recipients", get_suggested_recipients);
/** @type {RouteCallback} */
async function get_suggested_recipients(request) {
    const { thread_model, thread_id, partner_ids, main_email } = await parseRequestParams(request);
    const MailThread = this.env[thread_model];
    return MailThread._message_get_suggested_recipients([thread_id], partner_ids, main_email);
}

/** @type {RouteCallback} */
async function processRequest(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").MailGuest} */
    const MailGuest = this.env["mail.guest"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    /** @type {import("mock_models").MailNotification} */
    const MailNotification = this.env["mail.notification"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];
    /** @type {import("mock_models").ResUsers} */
    const ResUsers = this.env["res.users"];

    const store = new mailDataHelpers.Store();
    const args = await parseRequestParams(request);
    for (const fetchParam of args.fetch_params) {
        const [name, params] =
            typeof fetchParam === "string" || fetchParam instanceof String
                ? [fetchParam, undefined]
                : fetchParam;
        if (name === "init_messaging") {
            if (!MailGuest._get_guest_from_context() || !ResUsers._is_public(this.env.uid)) {
                ResUsers._init_messaging([this.env.uid], store, args.context);
            }
            const guest = ResUsers._is_public(this.env.uid) && MailGuest._get_guest_from_context();
            const members = DiscussChannelMember._filter([
                guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", this.env.user.partner_id],
                ["rtc_inviting_session_id", "!=", false],
            ]);
            const channelsDomain = [["id", "in", members.map((m) => m.channel_id)]];
            store.add(DiscussChannel.search(channelsDomain));
        }
        if (name === "failures" && this.env.user?.partner_id) {
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
        }
        if (name === "channels_as_member") {
            const channels = DiscussChannel._get_channels_as_member();
            store.add(
                MailMessage.browse(
                    channels
                        .map(
                            (channel) =>
                                MailMessage._filter([
                                    ["model", "=", "discuss.channel"],
                                    ["res_id", "=", channel.id],
                                ]).sort((a, b) => b.id - a.id)[0]
                        )
                        .filter((lastMessage) => lastMessage)
                        .map((message) => message.id)
                ),
                makeKwArgs({ for_current_user: true })
            );
            store.add(channels.map((channel) => channel.id));
        }
        if (name === "mail.thread") {
            store.add(
                this.env[params.thread_model].browse(params.thread_id),
                makeKwArgs({ as_thread: true, request_list: params.request_list })
            );
        }
        if (name === "discuss.channel") {
            const channels = DiscussChannel.search([["id", "=", params]]);
            store.add(channels);
            for (const channelId of params.filter((id) => !channels.includes(id))) {
                const channel = DiscussChannel.browse();
                // limitation of mock server: cannot browse non-existing record
                channel.push({ id: channelId });
                store.add(channel, makeKwArgs({ delete: true }));
            }
        }
        mailDataHelpers._process_request_for_internal_user.call(this, store, name, params);
    }
    return store;
}

function _process_request_for_internal_user(store, name, params) {
    /** @type {import("mock_models").ResUsers} */
    const ResUsers = this.env["res.users"];
    if (name === "systray_get_activities" && this.env.user?.partner_id) {
        const bus_last_id = this.env["bus.bus"].lastBusNotificationId;
        const groups = ResUsers._get_activity_groups();
        store.add({
            activityCounter: groups.reduce(
                (counter, group) => counter + (group.total_count || 0),
                0
            ),
            activity_counter_bus_id: bus_last_id,
            activityGroups: groups,
        });
    }
    if (name === "mail.canned.response") {
        const domain = [
            "|",
            ["create_uid", "=", this.env.user.id],
            ["group_ids", "in", this.env.user.group_ids],
        ];
        store.add(this.env["mail.canned.response"].search(domain));
    }
}

const ids_by_model = {
    "mail.thread": ["model", "id"],
    MessageReactions: ["message", "content"],
    Rtc: [],
    Store: [],
};

const MANY = Symbol("MANY");
const ONE = Symbol("ONE");

class Store {
    constructor(data, values, as_thread, _delete, kwargs) {
        this.data = new Map();
        if (data) {
            this.add(...arguments);
        }
    }

    add(data, values, as_thread, _delete, kwargs) {
        if (!data) {
            return this;
        }
        kwargs = unmakeKwArgs(getKwArgs(arguments, "data", "values", "as_thread", "delete"));
        data = kwargs.data;
        delete kwargs.data;
        values = kwargs.values;
        delete kwargs.values;
        as_thread = kwargs.as_thread;
        delete kwargs.as_thread;
        _delete = kwargs.delete ?? false;
        delete kwargs.delete;
        let model_name;
        if (data instanceof models.Model) {
            if (values) {
                if (data.length !== 1) {
                    throw new Error(`expected single recordset ${data} with values`);
                }
                if (Object.keys(kwargs).length) {
                    throw new Error(
                        `expected empty kwargs with recordset ${data} values: ${kwargs}`
                    );
                }
                if (_delete) {
                    throw new Error(`deleted not expected for ${data} with values: ${values}`);
                }
            }
            if (_delete) {
                if (data.length !== 1) {
                    throw new Error(`expected single record ${data} with delete`);
                }
                if (values) {
                    throw new Error(`for ${data} expected empty values with delete: ${values}`);
                }
            }
            const ids = data.map((idOrRecord) =>
                typeof idOrRecord === "number" ? idOrRecord : idOrRecord.id
            );
            if (as_thread) {
                if (_delete) {
                    this.add(
                        "mail.thread",
                        { id: data[0].id, model: data._name },
                        makeKwArgs({ delete: _delete })
                    );
                } else if (values) {
                    this.add("mail.thread", { id: data[0].id, model: data._name, ...values });
                } else {
                    MockServer.env["mail.thread"]._thread_to_store.call(
                        MockServer.env[data._name],
                        ids,
                        this,
                        makeKwArgs(kwargs)
                    );
                }
            } else {
                if (_delete) {
                    this.add(data._name, { id: ids[0] }, makeKwArgs({ delete: _delete }));
                } else if (values) {
                    this.add(data._name, { id: ids[0], ...values });
                } else {
                    MockServer.env[data._name]._to_store(ids, this, makeKwArgs(kwargs));
                }
            }
            return this;
        } else if (typeof data === "object") {
            if (values) {
                throw new Error(`expected empty values with dict ${data}: ${values}`);
            }
            if (Object.keys(kwargs).length) {
                throw new Error(`expected empty kwargs with dict ${data}: ${kwargs}`);
            }
            if (as_thread) {
                throw new Error(`expected not as_thread with dict ${data}: ${values}`);
            }
            model_name = "Store";
            values = data;
        } else {
            if (Object.keys(kwargs).length) {
                throw new Error(`expected empty kwargs with model name ${data}: ${kwargs}`);
            }
            if (as_thread) {
                throw new Error(`expected not as_thread with model name ${data}: ${values}`);
            }
            model_name = data;
        }
        if (typeof model_name !== "string") {
            throw new Error(`expected string for model name: ${model_name}: ${values}`);
        }
        const ids = ids_by_model[model_name] || ["id"];
        // handle singleton model: update single record in place
        if (!ids.length) {
            if (typeof values !== "object") {
                throw new Error(`expected dict for singleton ${model_name}: ${values}`);
            }
            if (_delete) {
                throw new Error(`Singleton ${model_name} cannot be deleted`);
            }
            if (!this.data.has(model_name)) {
                this.data.set(model_name, {});
            }
            this._add_values(values, model_name);
            return this;
        }
        // handle model with ids: add or update existing records based on ids
        if (!Array.isArray(values)) {
            if (!values) {
                return this;
            }
            values = [values];
        }
        if (!values.length) {
            return this;
        }
        let records = this.data.get(model_name);
        if (!records) {
            records = new Map();
            this.data.set(model_name, records);
        }
        for (const vals of values) {
            if (typeof vals !== "object") {
                throw new Error(`expected dict for ${model_name}: ${vals}`);
            }
            for (const i of ids) {
                if (!vals[i]) {
                    throw new Error(`missing id ${i} in ${model_name}: ${vals}`);
                }
            }
            const index = ids.map((i) => vals[i]).join(" AND ");
            if (!records.has(index)) {
                records.set(index, {});
            }
            this._add_values(vals, model_name, index);
            if (_delete) {
                records.get(index)._DELETE = true;
            } else {
                delete records.get(index)._DELETE;
            }
        }
        return this;
    }

    _add_values(values, model_name, index) {
        const target = index ? this.data.get(model_name).get(index) : this.data.get(model_name);
        for (const [key, val] of Object.entries(values)) {
            if (key === "_DELETE") {
                throw new Error(`invalid key ${key} in ${model_name}: ${values}`);
            }
            if (Array.isArray(val) && val[0] === ONE) {
                const [, subrecord, as_thread, only_id, subrecord_kwargs] = val;
                if (subrecord && !(subrecord instanceof models.Model)) {
                    throw new Error(`expected recordset for one ${key}: ${subrecord}`);
                }
                if (subrecord && subrecord.length && !only_id) {
                    this.add(subrecord, makeKwArgs({ as_thread, ...subrecord_kwargs }));
                }
                target[key] = Store.one_id(subrecord, makeKwArgs({ as_thread }));
            } else if (Array.isArray(val) && val[0] === MANY) {
                const [, subrecords, mode, as_thread, only_id, subrecords_kwargs] = val;
                if (subrecords && !(subrecords instanceof models.Model)) {
                    throw new Error(`expected recordset for many ${key}: ${subrecords}`);
                }
                if (!["ADD", "DELETE", "REPLACE"].includes(mode)) {
                    throw new Error(`invalid mode for many ${key}: ${mode} `);
                }
                if (subrecords && subrecords.length && !only_id) {
                    this.add(subrecords, makeKwArgs({ as_thread, ...subrecords_kwargs }));
                }
                const rel_val = Store.many_ids(subrecords, mode, makeKwArgs({ as_thread }));
                target[key] =
                    key in target && mode !== "REPLACE" ? target[key].concat(rel_val) : rel_val;
            } else {
                target[key] = val;
            }
        }
    }

    get_result() {
        const res = {};
        for (const [model_name, records] of this.data) {
            const ids = ids_by_model[model_name] || ["id"];
            if (!ids.length) {
                // singleton
                res[model_name] = { ...records };
            } else {
                res[model_name] = [...records.values()].map((record) => ({ ...record }));
            }
        }
        return res;
    }

    toJSON() {
        throw Error(
            "Converting Store to JSON is not supported, you might want to call 'get_result()' instead."
        );
    }

    static many(records, mode = "REPLACE", as_thread, only_id, kwargs) {
        kwargs = getKwArgs(arguments, "records", "mode");
        records = kwargs.records;
        delete kwargs.records;
        mode = kwargs.mode ?? "REPLACE";
        delete kwargs.mode;
        as_thread = kwargs.as_thread;
        delete kwargs.as_thread;
        only_id = kwargs.only_id;
        delete kwargs.only_id;
        if (records && !(records instanceof models.Model)) {
            throw new Error(`expected recordset for many: ${records}`);
        }
        return [MANY, records, mode, as_thread, only_id, makeKwArgs(kwargs)];
    }

    static one(records, as_thread, only_id, kwargs) {
        kwargs = getKwArgs(arguments, "records");
        records = kwargs.records;
        delete kwargs.records;
        as_thread = kwargs.as_thread;
        delete kwargs.as_thread;
        only_id = kwargs.only_id;
        delete kwargs.only_id;
        if (records && !(records instanceof models.Model)) {
            throw new Error(`expected recordset for one: ${records}`);
        }
        return [ONE, records, as_thread, only_id, makeKwArgs(kwargs)];
    }

    static many_ids(records, mode = "REPLACE", as_thread) {
        const kwargs = getKwArgs(arguments, "records", "mode");
        records = kwargs.records;
        mode = kwargs.mode ?? "REPLACE";
        as_thread = kwargs.as_thread;
        if (records && !(records instanceof models.Model)) {
            throw new Error(`expected recordset for many_ids: ${records}`);
        }
        if (!["ADD", "DELETE", "REPLACE"].includes(mode)) {
            throw new Error(`invalid mode for many_ids: ${mode} `);
        }
        let res = records.map((record) =>
            Store.one_id(records.browse(record.id), makeKwArgs({ as_thread }))
        );
        if (records._name === "mail.message.reaction") {
            res = [];
            const reactionGroups = groupBy(records, (r) => [r.message_id, r.content]);
            for (const groupId in reactionGroups) {
                const { message_id, content } = reactionGroups[groupId][0];
                res.push({ message: message_id, content: content });
            }
        }
        if (mode === "ADD") {
            res = [["ADD", res]];
        } else if (mode === "DELETE") {
            res = [["DELETE", res]];
        }
        return res;
    }

    static one_id(records, as_thread) {
        const kwargs = getKwArgs(arguments, "records");
        records = kwargs.records;
        as_thread = kwargs.as_thread;
        if (!records) {
            return false;
        }
        if (!(records instanceof models.Model)) {
            throw new Error(`expected recordset for one_id: ${records}`);
        }
        if (records.length > 1) {
            throw new Error(`expected none or single record for one_id: ${records}`);
        }
        const [record] = records;
        if (!record) {
            return false;
        }
        if (as_thread) {
            return { id: record.id, model: records._name };
        }
        if (records._name === "discuss.channel") {
            return { id: record.id, model: "discuss.channel" };
        }
        if (records._name === "mail.guest") {
            return { id: record.id, type: "guest" };
        }
        if (records._name === "res.partner") {
            return { id: record.id, type: "partner" };
        }
        return record.id;
    }
}

export const mailDataHelpers = {
    _process_request_for_internal_user,
    Store,
};
