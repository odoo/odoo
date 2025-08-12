import { markup } from "@odoo/owl";
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
import { createDocumentFragmentFromContent } from "@web/core/utils/html";

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
        res = await beforeCallableHandler?.after?.(response);
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
        rtc_session_ids: mailDataHelpers.Store.many(rtcSessions, makeKwArgs({ mode: "ADD" })),
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
                rtc_session_ids: mailDataHelpers.Store.many(
                    DiscussChannelRtcSession.browse(sessions.map((session) => session.id)),
                    makeKwArgs({ only_id: true, mode: "DELETE" })
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
        messages: messages.map((message) => message.id),
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
    const store = new mailDataHelpers.Store(DiscussChannel.browse(subChannels));
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
    const member = DiscussChannel._find_or_create_member_for_self(channel_id);
    DiscussChannelMember.write([member.id], { mute_until_dt });
    const [partner] = ResPartner.read(this.env.user.partner_id);
    BusBus._sendone(
        partner,
        "mail.record/insert",
        new mailDataHelpers.Store(DiscussChannelMember.browse([member.id]), {
            mute_until_dt,
        }).get_result()
    );
    return "dummy";
}

registerRoute("/discuss/settings/custom_notifications", discuss_custom_notifications);
/** @type {RouteCallback} */
async function discuss_custom_notifications(request) {
    /** @type {import("mock_models").ResUsersSettings} */
    const ResUsersSettings = this.env["res.users.settings"];
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];

    const { custom_notifications, channel_id } = await parseRequestParams(request);
    let record;
    let model;
    if (!channel_id) {
        record = ResUsersSettings._find_or_create_for_user(this.env.uid);
        model = ResUsersSettings;
    } else {
        record = DiscussChannel._find_or_create_member_for_self(channel_id);
        model = DiscussChannelMember;
    }
    if (!record) {
        return;
    }
    model.set_custom_notifications(record.id, custom_notifications);
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
        MailMessage.browse(messageIds),
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
        messages: mailDataHelpers.Store.many(messages)._get_id(),
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
        messages: messages.map((message) => message.id),
    };
}

registerRoute("/mail/link_preview$", mail_link_preview);
/** @type {RouteCallback} */
async function mail_link_preview(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").MailLinkPreview} */
    const MailLinkPreview = this.env["mail.link.preview"];
    /** @type {import("mock_models").MailLinkPreviewMessage} */
    const MailMessageLinkPreview = this.env["mail.message.link.preview"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { message_id } = await parseRequestParams(request);
    const [message] = MailMessage.search_read([["id", "=", message_id]]);
    const link = createDocumentFragmentFromContent(markup(message.body)).querySelector(
        "a[href^='https://tenor.com'], a[href='https://make-link-preview.com']"
    );
    if (link) {
        const isGifPreview = link.href.startsWith("https://tenor.com");
        const linkPreviewId = MailLinkPreview.create({
            og_description: isGifPreview ? "Click to view the GIF" : "test description",
            og_image: isGifPreview ? link.href : undefined,
            og_mimetype: isGifPreview ? "image/gif" : undefined,
            og_title: isGifPreview ? "Gif title" : "Article title",
            og_type: isGifPreview ? "video.other" : "article",
            source_url: isGifPreview ? link.href : "https://make-link-preview.com",
        });
        MailMessageLinkPreview.create({
            message_id: message.id,
            link_preview_id: linkPreviewId,
        });
        BusBus._sendone(
            MailMessage._bus_notification_target(message_id),
            "mail.record/insert",
            new mailDataHelpers.Store(MailMessage.browse(message_id)).get_result()
        );
    }
}

registerRoute("/mail/link_preview/hide$", mail_link_preview_hide);
/** @type {RouteCallback} */
async function mail_link_preview_hide(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").MailMessageLinkPreview} */
    const MailMessageLinkPreview = this.env["mail.message.link.preview"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { message_link_preview_ids } = await parseRequestParams(request);
    const messageLinkPreviews = MailMessageLinkPreview.browse(
        MailMessageLinkPreview.search([["id", "in", message_link_preview_ids]])
    );
    for (const messageLinkPreview of messageLinkPreviews) {
        messageLinkPreview.is_hidden = true;
        BusBus._sendone(
            MailMessage._bus_notification_target(messageLinkPreview.message_id),
            "mail.record/insert",
            new mailDataHelpers.Store(
                MailMessage.browse(messageLinkPreview.message_id)
            ).get_result()
        );
    }
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
    if (post_data.role_ids?.length) {
        const userIds = this.env["res.users"].search([["role_ids", "in", post_data.role_ids]]);
        const partnerIds = this.env["res.partner"].search([["user_ids", "in", userIds]]);
        post_data.partner_ids = [...new Set([...(post_data.partner_ids || []), ...partnerIds])];
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
    MailMessage.write([message_id], msg_values);
    BusBus._sendone(
        MailMessage._bus_notification_target(message.id),
        "mail.record/insert",
        new mailDataHelpers.Store(MailMessage.browse(message.id), {
            attachment_ids: mailDataHelpers.Store.many(IrAttachment.browse(message.attachment_ids)),
            body: ["markup", message.body],
            partner_ids: mailDataHelpers.Store.many(
                this.env["res.partner"].browse(message.partner_ids),
                makeKwArgs({ fields: ["avatar_128", "name"] })
            ),
            pinned_at: message.pinned_at,
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
    const subtypes = MailMessageSubtype.search([
        "&",
        ["hidden", "=", false],
        "|",
        ["res_model", "=", follower.res_model],
        ["res_model", "=", false],
    ]);
    return {
        store_data: new mailDataHelpers.Store(
            MailMessageSubtype.browse(subtypes),
            makeKwArgs({ fields: ["name"] })
        )
            .add(MailFollowers.browse(follower_id), makeKwArgs({ fields: ["subtype_ids"] }))
            .get_result(),
        subtype_ids: subtypes, // Not sorted for simplicity.
    };
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
        messages: messages.map((message) => message.id),
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
        messages: messages.map((message) => message.id),
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
    const args = await parseRequestParams(request);
    return processRequest.call(this, args.fetch_params, args.context).get_result();
}

registerRoute("/mail/data", mail_data);
/** @type {RouteCallback} */
export async function mail_data(request) {
    const args = await parseRequestParams(request);
    return processRequest.call(this, args.fetch_params, args.context).get_result();
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

registerRoute("/mail/thread/unsubscribe", mail_thread_unsubscribe);
/** @type {RouteCallback} */
async function mail_thread_unsubscribe(request) {
    const { res_model, res_id, partner_ids } = await parseRequestParams(request);
    const thread = this.env[res_model].browse(res_id);
    this.env["mail.thread"].message_unsubscribe.call(thread, [res_id], partner_ids);
    return new mailDataHelpers.Store(
        thread,
        makeKwArgs({ as_thread: true, request_list: ["followers", "suggestedRecipients"] })
    ).get_result();
}

registerRoute("/mail/thread/subscribe", mail_thread_subscribe);
/** @type {RouteCallback} */
async function mail_thread_subscribe(request) {
    const { res_model, res_id, partner_ids } = await parseRequestParams(request);
    const thread = this.env[res_model].browse(res_id);
    this.env["mail.thread"].message_subscribe.call(thread, [res_id], partner_ids);
    return new mailDataHelpers.Store(
        thread,
        makeKwArgs({ as_thread: true, request_list: ["followers", "suggestedRecipients"] })
    ).get_result();
}

function processRequest(fetchParams, context) {
    const store = new mailDataHelpers.Store();
    for (const fetchParam of fetchParams) {
        const [name, params, data_id] =
            typeof fetchParam === "string" || fetchParam instanceof String
                ? [fetchParam, undefined, undefined]
                : fetchParam;
        store.data_id = data_id;
        mailDataHelpers._process_request_for_all.call(this, store, name, params, context);
        mailDataHelpers._process_request_for_internal_user.call(this, store, name, params);
    }
    store.data_id = null;
    return store;
}

function _process_request_for_all(store, name, params, context = {}) {
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
    if (name === "init_messaging") {
        if (!MailGuest._get_guest_from_context() || !ResUsers._is_public(this.env.uid)) {
            ResUsers._init_messaging([this.env.uid], store, context);
        }
        const guest = ResUsers._is_public(this.env.uid) && MailGuest._get_guest_from_context();
        const members = DiscussChannelMember._filter([
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", this.env.user.partner_id],
            ["rtc_inviting_session_id", "!=", false],
        ]);
        const channelsDomain = [["id", "in", members.map((m) => m.channel_id)]];
        store.add(DiscussChannel.browse(DiscussChannel.search(channelsDomain)));
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
        store.add(channels);
    }
    if (name === "mail.thread") {
        store.add(
            this.env[params.thread_model].browse(params.thread_id),
            makeKwArgs({ as_thread: true, request_list: params.request_list })
        );
    }
    if (name === "discuss.channel") {
        const channels = DiscussChannel.search([["id", "=", params]]);
        store.add(DiscussChannel.browse(channels));
        for (const channelId of params.filter((id) => !channels.includes(id))) {
            const channel = DiscussChannel.browse();
            // limitation of mock server: cannot browse non-existing record
            channel.push({ id: channelId });
            store.add(channel, makeKwArgs({ delete: true }));
        }
    }
    if (name === "/discuss/get_or_create_chat") {
        const channelId = DiscussChannel._get_or_create_chat(params.partners_to);
        store.add(channelId).resolve_data_request({
            channel: mailDataHelpers.Store.one(channelId, makeKwArgs({ only_id: true })),
        });
    }
    if (name === "/discuss/create_channel") {
        const channelId = DiscussChannel._create_channel(params.name, params.group_id);
        store.add(channelId).resolve_data_request({
            channel: mailDataHelpers.Store.one(channelId, makeKwArgs({ only_id: true })),
        });
    }
    if (name === "/discuss/create_group") {
        const channelId = DiscussChannel._create_group(params.partners_to, params.name);
        store.add(channelId).resolve_data_request({
            channel: mailDataHelpers.Store.one(channelId, makeKwArgs({ only_id: true })),
        });
    }
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
        const CannedResponse = this.env["mail.canned.response"];
        const cannedResponses = CannedResponse.search(domain);
        store.add(CannedResponse.browse(cannedResponses));
    }
    if (name === "avatar_card") {
        const userId = params.user_id;
        const [user] = ResUsers.search([["id", "=", userId]]);
        if (user) {
            const fields = ResUsers._get_store_avatar_card_fields();
            store.add(ResUsers.browse(user), makeKwArgs({ fields }));
        }
    }
}

const ids_by_model = {
    "mail.thread": ["model", "id"],
    MessageReactions: ["message", "content"],
    Rtc: [],
    Store: [],
};

function extractAndDeleteKwArgs(args, ...keys) {
    const allKwargs = unmakeKwArgs(getKwArgs(args, ...keys));
    const kwargs = {};
    for (const key of keys) {
        if (Object.hasOwn(allKwargs, key)) {
            kwargs[key] = allKwargs[key];
            delete allKwargs[key];
        }
    }
    return [kwargs, allKwargs];
}

export class StoreAttr {
    constructor(name, value, predicate) {
        const [kwargs] = extractAndDeleteKwArgs(arguments, "name", "value", "predicate");
        this.name = kwargs.name;
        this.value = kwargs.value;
        this.predicate = kwargs.predicate;
    }

    _get_value(record, model = null) {
        if (typeof this.value === "function") {
            return this.value(record);
        }
        const value = this.value ?? record[this.name];
        return value;
    }
}

export class StoreRelation extends StoreAttr {
    constructor(name_or_record, fields, value, predicate, as_thread, only_id) {
        [{ name_or_record, fields, value, predicate, as_thread, only_id }] = extractAndDeleteKwArgs(
            arguments,
            "name_or_record",
            "fields",
            "value",
            "predicate",
            "as_thread",
            "only_id"
        );
        const name = typeof name_or_record === "string" ? name_or_record : null;
        super(makeKwArgs({ name, value }));
        this.records = name_or_record instanceof models.Model ? name_or_record : null;
        this.predicate = predicate;
        this.as_thread = as_thread;
        this.fields = fields;
        this.only_id = only_id;
    }
    _get_value(record, model) {
        let target = super._get_value(record);
        if (!target) {
            const res_model_field = model._fields["res_model"] ? "res_model" : "model";
            if (this.name === "thread" && !record["thread"]) {
                const res_model = record[res_model_field];
                const res_id = record["res_id"];
                if (res_model && res_id) {
                    target = model.env[res_model].browse(res_id);
                }
            }
        } else {
            const field = model._fields[this.name];

            target = model.env[field.relation].browse(target);
        }
        return this._copy_with_records(target, record);
    }

    _copy_with_records(target, record) {
        if (this.records) {
            throw new Error(`StoreRelation ${this.name} cannot be used with records`);
        }

        return new this.constructor(
            target,
            makeKwArgs({
                fields: this.fields,
                value: this.value,
                predicate: this.predicate,
                as_thread: this.as_thread,
            })
        );
    }

    _add_to_store(store, target, key) {
        if (!this.only_id) {
            store.add(this.records, this.fields, makeKwArgs({ as_thread: this.as_thread }));
        }
    }
}

export class StoreOne extends StoreRelation {
    _add_to_store(store, target, key) {
        super._add_to_store(store, target, key);
        target[key] = this._get_id();
    }
    _get_id() {
        if (!this.records || !this.records.length) {
            return false;
        }
        const id = this.records[0].id;
        if (this.as_thread) {
            return { id, model: this.records._name };
        }
        if (this.records._name === "discuss.channel") {
            return { id, model: "discuss.channel" };
        }
        return id;
    }
}

export class StoreMany extends StoreRelation {
    constructor(name_or_record, fields, value, predicate, as_thread, mode, only_id, sort) {
        const [kwargs] = extractAndDeleteKwArgs(
            arguments,
            "name_or_record",
            "fields",
            "value",
            "predicate",
            "as_thread",
            "mode",
            "only_id",
            "sort"
        );
        name_or_record = kwargs.name_or_record;
        fields = kwargs.fields;
        value = kwargs.value;
        predicate = kwargs.predicate;
        as_thread = kwargs.as_thread;
        mode = kwargs.mode || "REPLACE";
        only_id = kwargs.only_id || false;
        sort = kwargs.sort || false;
        super(
            name_or_record,
            makeKwArgs({
                fields,
                value,
                predicate,
                as_thread,
                only_id,
            })
        );
        this.mode = mode;
    }
    _copy_with_records(target, record) {
        const res = super._copy_with_records(target, record);
        res.mode = this.mode;
        res.sort = this.sort;
        return res;
    }

    _sort_records() {
        if (this.sort) {
            this.records.sort(this.sort);
            this.sort = false;
        }
    }
    _add_to_store(store, target, key) {
        this._sort_records();
        super._add_to_store(store, target, key);
        const rel_val = this._get_id();
        const previous_value = this.mode !== "REPLACE" ? target[key] : undefined;
        target[key] = (previous_value || []).concat(rel_val);
    }
    _get_id() {
        if (!this.records || !this.records.length) {
            return [];
        }
        const res = [];

        if (this.records._name === "mail.message.reaction") {
            const reactionGroups = groupBy(this.records, (r) => [r.message_id, r.content]);
            for (const groupId in reactionGroups) {
                const { message_id, content } = reactionGroups[groupId][0];
                res.push({ message: message_id, content: content });
            }
        } else {
            for (const record of this.records) {
                res.push(
                    new StoreOne(
                        this.records.env[this.records._name].browse(record.id),
                        makeKwArgs({
                            as_thread: this.as_thread,
                        })
                    )._get_id()
                );
            }
        }
        if (["ADD", "DELETE"].includes(this.mode)) {
            return [[this.mode, res]];
        }
        return res;
    }
}

class Store {
    constructor(data, fields, as_thread, _delete, kwargs) {
        this.data = new Map();
        this.data_id = null;
        if (data) {
            this.add(...arguments);
        }
    }

    add(data, fields, as_thread, _delete, extra_fields, kwargs) {
        if (!data) {
            return this;
        }
        [{ data, fields, as_thread, delete: _delete, extra_fields }, kwargs] =
            extractAndDeleteKwArgs(
                arguments,
                "data",
                "fields",
                "as_thread",
                "delete",
                "extra_fields"
            );
        _delete = _delete ?? false;
        let model_name;
        if (data instanceof models.Model) {
            if (fields) {
                if (Object.keys(kwargs).length) {
                    throw new Error(
                        `expected empty kwargs with recordset ${data} values: ${kwargs}`
                    );
                }
                if (_delete) {
                    throw new Error(`deleted not expected for ${data} with values: ${fields}`);
                }
            }
            if (_delete) {
                if (data.length !== 1) {
                    throw new Error(`expected single record ${data} with delete`);
                }
                if (fields) {
                    throw new Error(`for ${data} expected empty values with delete: ${fields}`);
                }
            }
            const ids = data.map((idOrRecord) =>
                typeof idOrRecord === "number" ? idOrRecord : idOrRecord.id
            );
            if (_delete) {
                if (as_thread) {
                    this._add_model_values(
                        "mail.thread",
                        { id: data[0].id, model: data._name },
                        makeKwArgs({ delete: _delete })
                    );
                } else {
                    this._add_model_values(
                        data._name,
                        { id: ids[0] },
                        makeKwArgs({ delete: _delete })
                    );
                }
            } else {
                if (!fields) {
                    if (as_thread) {
                        fields = [];
                    } else {
                        fields = data._to_store_defaults || [];
                    }
                }
                fields = this._format_fields(fields).concat(this._format_fields(extra_fields));
                if (as_thread) {
                    MockServer.env["mail.thread"]._thread_to_store.call(
                        data,
                        this,
                        fields,
                        makeKwArgs(kwargs)
                    );
                } else {
                    if (data._to_store) {
                        data._to_store(this, fields, makeKwArgs(kwargs));
                    } else {
                        this._add_record_fields(data, fields, as_thread);
                    }
                }
            }
            return this;
        } else if (typeof data === "object") {
            if (fields) {
                throw new Error(`expected empty values with dict ${data}: ${fields}`);
            }
            if (Object.keys(kwargs).length) {
                throw new Error(`expected empty kwargs with dict ${data}: ${kwargs}`);
            }
            if (as_thread) {
                throw new Error(`expected not as_thread with dict ${data}: ${fields}`);
            }
            model_name = "Store";
            fields = data;
        } else {
            if (Object.keys(kwargs).length) {
                throw new Error(`expected empty kwargs with model name ${data}: ${kwargs}`);
            }
            if (as_thread) {
                throw new Error(`expected not as_thread with model name ${data}: ${fields}`);
            }
            model_name = data;
        }
        return this._add_model_values(model_name, fields, _delete);
    }

    _get_records_data_list(records, fields) {
        const abstractedFields = fields.filter((field) => field instanceof StoreAttr);
        const records_data_list = records
            ._read_format(
                records.map((r) => r.id),
                fields.filter((f) => !abstractedFields.includes(f)),
                false
            )
            .map((data) => [data]);
        for (const index in records_data_list) {
            const record = records[index];
            for (const field of abstractedFields) {
                if (field instanceof StoreAttr) {
                    if (!field.predicate || field.predicate(record)) {
                        const field_data = {};
                        field_data[field.name] = field._get_value(record, records);
                        records_data_list[index].push(field_data);
                    }
                } else {
                    records_data_list[index].push(field);
                }
            }
        }
        return records_data_list;
    }

    _add_record_fields(records, fields, as_thread) {
        if (!records || !records.length) {
            return this;
        }
        if (!(records instanceof models.Model)) {
            throw new Error(`expected recordset for _add_record_fields: ${records}`);
        }
        fields = this._format_fields(fields);
        const data_list = this._get_records_data_list(records, fields);
        const model_name = records._name;
        for (const index in data_list) {
            for (const data of data_list[index]) {
                if (as_thread) {
                    this._add_model_values("mail.thread", {
                        id: records[index].id,
                        model: model_name,
                        ...data,
                    });
                } else {
                    this._add_model_values(model_name, {
                        id: records[index].id,
                        ...data,
                    });
                }
            }
        }
        return this;
    }
    _add_model_values(model_name, values, _delete) {
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

    _format_fields(fields) {
        if (fields === null || fields === undefined) {
            return [];
        } else if (
            typeof fields === "object" &&
            !Array.isArray(fields) &&
            !(fields instanceof StoreAttr)
        ) {
            fields = Object.entries(fields).map(
                ([key, value]) => new StoreAttr(makeKwArgs({ name: key, value }))
            );
        }
        if (!Array.isArray(fields)) {
            fields = [fields];
        }
        return fields;
    }

    _add_values(values, model_name, index) {
        const target = index ? this.data.get(model_name).get(index) : this.data.get(model_name);
        for (const [key, val] of Object.entries(values)) {
            if (key === "_DELETE") {
                throw new Error(`invalid key ${key} in ${model_name}: ${values}`);
            }
            if (val instanceof StoreRelation) {
                val._add_to_store(this, target, key);
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

    resolve_data_request(values) {
        if (this.data_id) {
            this._add_model_values("DataResponse", { id: this.data_id, _resolve: true, ...values });
        }
        return this;
    }

    toJSON() {
        throw Error(
            "Converting Store to JSON is not supported, you might want to call 'get_result()' instead."
        );
    }

    static many(records, fields, mode = "REPLACE", as_thread, kwargs) {
        let otherKwArgs;
        [kwargs, otherKwArgs] = extractAndDeleteKwArgs(
            arguments,
            "records",
            "fields",
            "mode",
            "as_thread"
        );
        records = kwargs.records;
        fields = kwargs.fields;
        mode = kwargs.mode ?? "REPLACE";
        as_thread = kwargs.as_thread;
        return new StoreMany(
            records,
            makeKwArgs({
                fields: fields,
                mode,
                as_thread,
                ...otherKwArgs,
            })
        );
    }

    static one(records, fields, as_thread, kwargs) {
        let otherKwArgs;
        [kwargs, otherKwArgs] = extractAndDeleteKwArgs(arguments, "records", "fields", "as_thread");
        records = kwargs.records;
        fields = kwargs.fields;
        as_thread = kwargs.as_thread;
        return new StoreOne(
            records,
            makeKwArgs({
                fields: fields,
                as_thread,
                ...otherKwArgs,
            })
        );
    }

    static attr(name, value, predicate) {
        [{ name, value, predicate }] = extractAndDeleteKwArgs(
            arguments,
            "name",
            "value",
            "predicate"
        );
        return new StoreAttr(makeKwArgs({ name, value, predicate }));
    }
}

export const mailDataHelpers = {
    _process_request_for_all,
    _process_request_for_internal_user,
    Store,
};
