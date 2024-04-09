import { MockServer, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import {
    Kwargs,
    MockServerError,
    isKwargs,
} from "@web/../tests/_framework/mock_server/mock_server_utils";
import { authenticate, logout } from "@web/../tests/_framework/mock_server/mock_server";
import { session } from "@web/session";

export const DISCUSS_ACTION_ID = 104;

/**
 * @template [T={}]
 * @typedef {import("@web/../tests/web_test_helpers").RouteCallback<T>} RouteCallback
 */

const { DateTime } = luxon;

/**
 * @param {Array} param arguments of method
 * @param  {...string} argNames ordered names of positional arguments
 * @returns {Object} kwargs normalized params
 */
export const parseModelParams = (params, ...argNames) => {
    const params2 = [...params];
    const last = params2[params2.length - 1];
    let args;
    let kwargs = Kwargs({});
    if (isKwargs(last)) {
        kwargs = last;
        params2.pop();
        args = [...params2];
    } else {
        args = [...params2];
    }
    if (args.length > argNames.length) {
        throw "more positional args than there are defined arg names";
    }
    for (let i = 0; i < args.length; i++) {
        if (argNames[i] in kwargs) {
            continue;
        }
        kwargs[argNames[i]] = args[i];
    }
    return kwargs;
};

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
    session.user_id = false;
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
    const [targetGuest] = MailGuest._filter([["id", "=", guestId]], { active_test: false });
    const OLD_SESSION_USER_ID = session.user_id;
    authenticateGuest(targetGuest);
    session.user_id = false;
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
        session.user_id = OLD_SESSION_USER_ID;
    }
    return result;
}

/** @param {Request} request */
export const parseRequestParams = async (request) => {
    const response = await request.json();
    return response.params;
};

const onRpcBeforeGlobal = {
    cb: (route, args) => {},
};
// using a registry category to not expose for manual import
// We should use `onRpcBefore` with 1st parameter being (route, args) callback function
registry.category("mail.on_rpc_before_global").add(true, onRpcBeforeGlobal);
export function registerRoute(route, handler) {
    const beforeCallableHandler = async function (request) {
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
        return handler.call(this, request);
    };
    registry.category("mock_rpc").add(route, beforeCallableHandler);
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
    return IrAttachment._attachment_format([attachmentId])[0];
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
    return IrAttachment._attachment_format(attachmentIds);
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
        guest_id: memberOfCurrentUser.guest_id[0],
        partner_id: memberOfCurrentUser.partner_id[0],
    });
    const channelMembers = DiscussChannelMember._filter([["channel_id", "=", channel_id]]);
    const rtcSessions = DiscussChannelRtcSession._filter([
        ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
    ]);
    return {
        iceServers: false,
        rtcSessions: [
            [
                "ADD",
                rtcSessions.map((rtcSession) =>
                    DiscussChannelRtcSession._mail_rtc_session_format(rtcSession.id)
                ),
            ],
        ],
        sessionId: sessionId,
    };
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
    const channelInfo = DiscussChannelRtcSession._mail_rtc_session_format_by_channel(
        rtcSessions.map((rtcSession) => rtcSession.id)
    );
    for (const [channelId, sessionsData] of Object.entries(channelInfo)) {
        const channel = DiscussChannel.search_read([["id", "=", parseInt(channelId)]])[0];
        const notificationRtcSessions = sessionsData.map((sessionsDataPoint) => {
            return { id: sessionsDataPoint.id };
        });
        notifications.push([
            channel,
            "discuss.channel/rtc_sessions_update",
            {
                id: Number(channelId), // JS object keys are strings, but the type from the server is number
                rtcSessions: [["DELETE", notificationRtcSessions]],
            },
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

registerRoute("/discuss/channel/fold", discuss_channel_fold);
/** @type {RouteCallback} */
async function discuss_channel_fold(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];

    const { channel_id, state, state_count } = await parseRequestParams(request);
    const memberOfCurrentUser = DiscussChannel._find_or_create_member_for_self(channel_id);
    return DiscussChannelMember._channel_fold(memberOfCurrentUser.id, state, state_count);
}

registerRoute("/discuss/channel/info", discuss_channel_info);
/** @type {RouteCallback} */
async function discuss_channel_info(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id } = await parseRequestParams(request);
    return DiscussChannel._channel_info([channel_id])[0];
}

registerRoute("/discuss/channel/members", discuss_channel_members);
/** @type {RouteCallback} */
async function discuss_channel_members(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id, known_member_ids } = await parseRequestParams(request);
    return DiscussChannel.load_more_members([channel_id], known_member_ids);
}

registerRoute("/discuss/channel/messages", discuss_channel_messages);
/** @type {RouteCallback} */
async function discuss_channel_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const {
        after,
        around,
        before,
        channel_id,
        limit = 30,
        search_term,
    } = await parseRequestParams(request);
    const domain = [
        ["res_id", "=", channel_id],
        ["model", "=", "discuss.channel"],
        ["message_type", "!=", "user_notification"],
    ];
    const res = MailMessage._message_fetch(domain, search_term, before, after, around, limit);
    if (!around) {
        MailMessage.set_message_done(res.messages.map((message) => message.id));
    }
    return {
        ...res,
        messages: MailMessage._message_format(res.messages.map((message) => message.id)),
    };
}

registerRoute("/discuss/channel/mute", discuss_channel_mute);
/** @type {RouteCallback} */
async function discuss_channel_mute(request) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { channel_id, minutes } = await parseRequestParams(request);
    const member = DiscussChannel._find_or_create_member_for_self(channel_id);
    let mute_until_dt;
    if (minutes === -1) {
        mute_until_dt = serializeDateTime(DateTime.fromISO("9999-12-31T23:59:59"));
    } else if (minutes) {
        mute_until_dt = serializeDateTime(DateTime.now().plus({ minutes }));
    } else {
        mute_until_dt = false;
    }
    DiscussChannelMember.write([member.id], { mute_until_dt });
    const channel_data = {
        id: member.channel_id[0],
        model: "discuss.channel",
        mute_until_dt,
    };
    const [partner] = ResPartner.read(this.env.user.partner_id);
    BusBus._sendone(partner, "mail.record/insert", { Thread: channel_data });
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
    return MailMessage._message_format(messageIds);
}

registerRoute("/discuss/channel/set_last_seen_message", discuss_channel_mark_as_seen);
/** @type {RouteCallback} */
async function discuss_channel_mark_as_seen(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id, last_message_id } = await parseRequestParams(request);
    return DiscussChannel._channel_seen([channel_id], last_message_id);
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

    const { after, before, limit = 30, search_term } = await parseRequestParams(request);
    const domain = [["needaction", "=", false]];
    const res = MailMessage._message_fetch(domain, search_term, before, after, false, limit);
    const messagesWithNotification = res.messages.filter((message) => {
        const notifs = MailNotification.search_read([
            ["mail_message_id", "=", message.id],
            ["is_read", "=", true],
            ["res_partner_id", "=", this.env.user.partner_id],
        ]);
        return notifs.length > 0;
    });

    return {
        ...res,
        messages: MailMessage._message_format(messagesWithNotification.map((message) => message.id)),
    };
}

registerRoute("/mail/inbox/messages", discuss_inbox_messages);
/** @type {RouteCallback} */
async function discuss_inbox_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { after, around, before, limit = 30, search_term } = await parseRequestParams(request);
    const domain = [["needaction", "=", true]];
    const res = MailMessage._message_fetch(domain, search_term, before, after, around, limit);
    return {
        ...res,
        messages: MailMessage._message_format_personalize(
            res.messages.map((message) => message.id)
        ),
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
    const linkPreviews = [];
    const [message] = MailMessage.search_read([["id", "=", message_id]]);
    if (message.body.includes("https://make-link-preview.com")) {
        const linkPreviewId = MailLinkPreview.create({
            message_id: message.id,
            og_description: "test description",
            og_title: "Article title",
            og_type: "article",
            source_url: "https://make-link-preview.com",
        });
        const [linkPreview] = MailLinkPreview.search_read([["id", "=", linkPreviewId]]);
        linkPreviews.push(MailLinkPreview._link_preview_format(linkPreview));
        BusBus._sendone(MailMessage._bus_notification_target(message_id), "mail.record/insert", {
            LinkPreview: linkPreviews,
        });
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
    const linkPreviews = MailLinkPreview.search_read([["id", "in", link_preview_ids]]);
    for (const linkPreview of linkPreviews) {
        BusBus._sendone(
            MailMessage._bus_notification_target(linkPreview.message_id[0]),
            "mail.record/insert",
            {
                Message: {
                    id: linkPreview.message_id[0],
                    linkPreviews: [["DELETE", [{ id: linkPreview.id }]]],
                },
            }
        );
    }
    return { link_preview_ids };
}

registerRoute("/mail/message/post", mail_message_post);
/** @type {RouteCallback} */
export async function mail_message_post(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").MailThread} */
    const MailThread = this.env["mail.thread"];

    const { context, post_data, thread_id, thread_model } = await parseRequestParams(request);
    const finalData = {};
    for (const allowedField of [
        "attachment_ids",
        "body",
        "message_type",
        "partner_ids",
        "subtype_xmlid",
        "parent_id",
        "partner_emails",
        "partner_additional_values",
    ]) {
        if (post_data[allowedField] !== undefined) {
            finalData[allowedField] = post_data[allowedField];
        }
    }
    const kwargs = Kwargs({ ...finalData, context });
    if (thread_model === "discuss.channel") {
        return DiscussChannel.message_post(thread_id, kwargs);
    }
    const model = this.env[thread_model];
    return MailThread.message_post.call(
        model,
        [thread_id],
        Kwargs({ ...kwargs, model: thread_model })
    );
}

registerRoute("/mail/message/reaction", mail_message_add_reaction);
/** @type {RouteCallback} */
async function mail_message_add_reaction(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { action, content, message_id } = await parseRequestParams(request);
    return MailMessage._message_reaction(message_id, content, action);
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
    MailMessage.write([message_id], { body, attachment_ids });
    if (body === "") {
        MailMessage.write([message_id], { pinned_at: false });
    }
    const [message] = MailMessage.search_read([["id", "=", message_id]]);
    BusBus._sendone(MailMessage._bus_notification_target(message_id), "mail.record/insert", {
        Message: {
            id: message_id,
            body,
            attachments: IrAttachment._attachment_format(attachment_ids),
            pinned_at: message.pinned_at,
        },
    });
    return MailMessage._message_format([message_id])[0];
}

registerRoute("/discuss/channel/:cid/partner/:pid/avatar_128", partnerAvatar128);
/** @type {RouteCallback} */
async function partnerAvatar128(request, { cid, pid }) {
    return [cid, pid];
}

registerRoute("/mail/partner/from_email", mail_thread_partner_from_email);
/** @type {RouteCallback} */
async function mail_thread_partner_from_email(request) {
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const { emails, additional_values = {} } = await parseRequestParams(request);
    const partners = emails.map((email) => ResPartner.search([["email", "=", email]])[0]);
    for (const index in partners) {
        if (!partners[index]) {
            const email = emails[index];
            partners[index] = ResPartner.create({
                email,
                name: email,
                ...(additional_values[email] || {}),
            });
        }
    }
    return partners.map((partner_id) => {
        const partner = ResPartner._filter([["id", "=", partner_id]])[0];
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
    const follower = MailFollowers._filter([["id", "=", follower_id]])[0];
    const subtypes = MailMessageSubtype._filter([
        "&",
        ["hidden", "=", false],
        "|",
        ["res_model", "=", follower.res_model],
        ["res_model", "=", false],
    ]);
    const subtypes_list = subtypes.map((subtype) => {
        const parent = MailMessageSubtype._filter([["id", "=", subtype.parent_id]])[0];
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

    const { after, before, limit = 30, search_term } = await parseRequestParams(request);
    const domain = [["starred_partner_ids", "in", [this.env.user.partner_id]]];
    const res = MailMessage._message_fetch(domain, search_term, before, after, false, limit);
    return {
        ...res,
        messages: MailMessage._message_format(res.messages.map((message) => message.id)),
    };
}

registerRoute("/mail/thread/data", mail_thread_data);
/** @type {RouteCallback} */
async function mail_thread_data(request) {
    /** @type {import("mock_models").MailThread} */
    const MailThread = this.env["mail.thread"];

    const { request_list, thread_model, thread_id } = await parseRequestParams(request);
    return MailThread._get_mail_thread_data.call(this.env[thread_model], thread_id, request_list);
}

registerRoute("/mail/thread/messages", mail_thread_messages);
/** @type {RouteCallback} */
async function mail_thread_messages(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { after, around, before, limit, search_term, thread_id, thread_model } =
        await parseRequestParams(request);
    const domain = [
        ["res_id", "=", thread_id],
        ["model", "=", thread_model],
        ["message_type", "!=", "user_notification"],
    ];
    const res = MailMessage._message_fetch(domain, search_term, before, after, around, limit);
    MailMessage.set_message_done(res.messages.map((message) => message.id));
    return {
        ...res,
        messages: MailMessage._message_format(res.messages.map((message) => message.id)),
    };
}

registerRoute("/mail/action", mail_action);
/** @type {RouteCallback} */
async function mail_action(request) {
    return mailDataHelpers.processRequest.call(this, request);
}

registerRoute("/mail/data", mail_data);
/** @type {RouteCallback} */
async function mail_data(request) {
    return mailDataHelpers.processRequest.call(this, request);
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

    const res = {};
    const args = await parseRequestParams(request);
    if ("init_messaging" in args) {
        const initMessaging =
            MailGuest._get_guest_from_context() && ResUsers._is_public(this.env.uid)
                ? {}
                : ResUsers._init_messaging([this.env.uid], args.context);
        addToRes(res, initMessaging);
        const guest = ResUsers._is_public(this.env.uid) && MailGuest._get_guest_from_context();
        const members = DiscussChannelMember._filter([
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", this.env.user.partner_id],
            "|",
            ["fold_state", "in", ["open", "folded"]],
            ["rtc_inviting_session_id", "!=", false],
        ]);
        const channelsDomain = [["id", "in", members.map((m) => m.channel_id)]];
        const { channelTypes } = args.init_messaging;
        if (channelTypes) {
            channelsDomain.push(["channel_type", "in", channelTypes]);
        }
        addToRes(res, {
            Thread: DiscussChannel._channel_info(DiscussChannel.search(channelsDomain)),
        });
    }
    if (args.failures && this.env.user?.partner_id) {
        const partner = ResPartner._filter([["id", "=", this.env.user.partner_id]], {
            active_test: false,
        })[0];
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
        addToRes(res, {
            Message: MailMessage._message_notification_format(
                messages.map((message) => message.id)
            ),
        });
    }
    if (args.systray_get_activities && this.env.user?.partner_id) {
        const bus_last_id = this.env["bus.bus"].lastBusNotificationId;
        const groups = ResUsers._get_activity_groups();
        addToRes(res, {
            Store: {
                activityCounter: groups.reduce(
                    (counter, group) => counter + (group.total_count || 0),
                    0
                ),
                activity_counter_bus_id: bus_last_id,
                activityGroups: groups,
            },
        });
    }
    if (args.channels_as_member) {
        const channels = DiscussChannel._get_channels_as_member();
        addToRes(res, {
            Message: channels
                .map((channel) => {
                    const channelMessages = MailMessage._filter([
                        ["model", "=", "discuss.channel"],
                        ["res_id", "=", channel.id],
                    ]);
                    const lastMessage = channelMessages.reduce((lastMessage, message) => {
                        if (message.id > lastMessage.id) {
                            return message;
                        }
                        return lastMessage;
                    }, channelMessages[0]);
                    return lastMessage ? MailMessage._message_format([lastMessage.id])[0] : false;
                })
                .filter((lastMessage) => lastMessage),
            Thread: DiscussChannel._channel_info(channels.map((channel) => channel.id)),
        });
    }
    if (args.canned_responses) {
        const domain = [
            "|",
            ["create_uid", "=", this.env.user.id],
            ["group_ids", "in", this.env.user.groups_id.map((group) => group.id)],
        ];
        addToRes(res, {
            CannedResponse: this.env["mail.canned.response"].search_read(domain, {
                fields: ["source", "substitution"],
            }),
        });
    }
    return res;
}

function addToRes(res, data) {
    for (const [key, val] of Object.entries(data)) {
        if (Array.isArray(val)) {
            if (!res[key]) {
                res[key] = val;
            } else {
                res[key].push(...val);
            }
        } else if (typeof val === "object" && val !== null) {
            if (!res[key]) {
                res[key] = val;
            } else {
                Object.assign(res[key], val);
            }
        } else {
            throw new Error("Unsupported return type");
        }
    }
}

export const mailDataHelpers = {
    addToRes,
    processRequest,
};
