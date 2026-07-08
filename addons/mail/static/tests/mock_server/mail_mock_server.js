import { Store } from "@mail/../tests/mock_server/store";
import { storeHandlerRegistry } from "@mail/../tests/mock_server/store_handler";
import { markup } from "@odoo/owl";
import {
    authenticate,
    logout,
    makeKwArgs,
    MockServer,
    MockServerError,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
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

    const body = await request.formData();
    const ufile = body.get("ufile");
    const is_pending = body.get("is_pending") === "true";
    const model = is_pending ? "mail.compose.message" : body.get("thread_model");
    const id = is_pending ? 0 : parseInt(body.get("thread_id"));
    const attachmentId = IrAttachment.create({
        mimetype: ufile.type,
        name: ufile.name,
        res_id: id,
        res_model: model,
    });
    if (body.get("voice")) {
        DiscussVoiceMetadata.create({ attachment_id: attachmentId });
    }
    return {
        data: {
            attachment_id: attachmentId,
            store_data: new Store()
                .add(IrAttachment.browse(attachmentId), "_store_attachment_fields")
                .as_dict(),
        },
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
    return {
        count: attachmentIds.length,
        store_data: new Store()
            .add(IrAttachment.browse(attachmentIds), "_store_attachment_fields")
            .as_dict(),
    };
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
    return new Store()
        .add(DiscussChannel.browse(channel_id), (res) =>
            res.many("rtc_session_ids", "_store_rtc_session_fields", {
                mode: "ADD",
                value: rtcSessions,
            })
        )
        .add_model_values("Rtc", (res) => {
            res.attr("iceServers", false);
            res.one("localSession", "_store_rtc_session_fields", {
                value: DiscussChannelRtcSession.browse(sessionId),
            });
        })
        .as_dict();
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
    const channelMembers = DiscussChannelMember._filter([
        ["channel_id", "=", channel_id],
        ["is_self", "=", true],
    ]);
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
            new Store()
                .add(DiscussChannel.browse(Number(channelId)), (res) =>
                    res.many("rtc_session_ids", [], {
                        mode: "DELETE",
                        value: DiscussChannelRtcSession.browse(
                            sessions.map((session) => session.id)
                        ),
                    })
                )
                .as_dict(),
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
    this.env["discuss.channel.rtc.session"].unlink(Array.from(rtcSessions).map(({ id }) => id));
    BusBus._sendmany(notifications);
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

registerRoute("/discuss/channel/sub_channel/delete", discuss_channel_sub_channel_delete);
async function discuss_channel_sub_channel_delete(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];
    const { sub_channel_id } = await parseRequestParams(request);
    const [partner] = ResPartner.read(this.env.user.partner_id);
    const [subChannel] = DiscussChannel.read(sub_channel_id);
    if (subChannel.author_id[0] !== partner.id) {
        return;
    }
    const [sub_channel] = DiscussChannel.browse(sub_channel_id);
    DiscussChannel.message_post(
        sub_channel.parent_channel_id,
        makeKwArgs({
            body: `<div data-oe-type="thread_deletion" class="o_mail_notification">${sub_channel.name}</div>`,
            message_type: "notification",
            subtype_xmlid: "mail.mt_comment",
        })
    );
    DiscussChannel.unlink([sub_channel_id]);
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
    const store = new Store().add(DiscussChannel.browse(subChannels), "_store_channel_fields");
    const lastMessageIds = [];
    for (const channel of subChannels) {
        const lastMessageId = Math.max(channel.message_ids);
        if (lastMessageId) {
            lastMessageIds.push(lastMessageId);
        }
    }
    store.add(MailMessage.browse(lastMessageIds), "_store_message_fields");
    return {
        store_data: store.as_dict(),
        sub_channel_ids: subChannels,
    };
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
        new Store().add(DiscussChannelMember.browse([member.id]), { mute_until_dt }).as_dict()
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

registerRoute("/mail/link_preview", mail_link_preview);
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
        "a[href^='https://tenor.com'], a[href^='https://make-link-preview.com']"
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
            new Store().add(MailMessage.browse(message_id), "_store_message_fields").as_dict()
        );
    }
}

registerRoute("/mail/link_preview/hide", mail_link_preview_hide);
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
            new Store()
                .add(MailMessage.browse(messageLinkPreview.message_id), "_store_message_fields")
                .as_dict()
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

    const { context, post_data, thread_id, thread_model, canned_response_ids } =
        await parseRequestParams(request);
    if (canned_response_ids) {
        for (const cannedResponseId of canned_response_ids) {
            this.env["mail.canned.response"].write([cannedResponseId], {
                last_used: serializeDateTime(DateTime.now()),
            });
        }
    }
    if (post_data.partner_emails) {
        post_data.partner_ids = post_data.partner_ids || [];
        for (const email of post_data.partner_emails) {
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
        "needaction",
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
    return {
        message_id: messageIds[0],
        store_data: new Store()
            .add(MailMessage.browse(messageIds[0]), "_store_message_fields")
            .as_dict(),
    };
}

registerRoute("/mail/message/reaction", mail_message_reaction);
/** @type {RouteCallback} */
async function mail_message_reaction(request) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    const { action, content, message_id } = await parseRequestParams(request);
    const partner_id = this.env.user?.partner_id ?? false;
    const guest_id = this.env.cookie.get("dgid") ?? false;
    const store = new Store();
    MailMessage._message_reaction(message_id, content, partner_id, guest_id, action, store);
    return store.as_dict();
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
    /** @type {import("mock_models").MailMessageLinkPreview} */
    const MailMessageLinkPreview = this.env["mail.message.link.preview"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];

    const { message_id, update_data } = await parseRequestParams(request);
    const [message] = MailMessage.browse(message_id);
    const msg_values = {};
    if (update_data.body !== null) {
        const edit_label = `<span class='o-mail-Message-edited' data-o-datetime="${serializeDateTime(
            DateTime.now()
        )}"/>`;
        if (update_data.body === "" && update_data.attachment_ids.length === 0) {
            msg_values.body = "";
        } else {
            const div = document.createElement("div");
            div.innerHTML = update_data.body;
            const children = [...div.children];
            if (children.length > 0) {
                const lastChild = children[children.length - 1];
                const target = ["DIV", "P"].includes(lastChild.tagName) ? lastChild : div;
                target.insertAdjacentHTML("beforeend", edit_label);
                msg_values.body = div.innerHTML;
            } else {
                msg_values.body = update_data.body + edit_label;
            }
        }
    }
    if (update_data.attachment_ids.length === 0) {
        IrAttachment.unlink(message.attachment_ids);
    } else {
        const attachments = IrAttachment.browse(update_data.attachment_ids).filter(
            (attachment) =>
                attachment.res_model === "mail.compose.message" &&
                attachment.create_uid === this.env.user?.id
        );
        IrAttachment.write(
            attachments.map((attachment) => attachment.id),
            {
                res_model: message.model,
                res_id: message.res_id,
            }
        );
        msg_values.attachment_ids = update_data.attachment_ids;
    }
    if (update_data.body === "") {
        MailMessageLinkPreview.unlink(message.message_link_preview_ids);
    }
    if (!update_data.body && update_data.attachment_ids.length === 0) {
        msg_values.partner_ids = false;
        msg_values.parent_id = false;
    }
    if ("subject" in update_data) {
        msg_values.subject = update_data.subject;
    }
    MailMessage.write([message_id], msg_values);
    BusBus._sendone(
        MailMessage._bus_notification_target(message.id),
        "mail.record/insert",
        new Store()
            .add(MailMessage.browse(message.id), (res) => {
                res.many("attachment_ids", "_store_attachment_fields", {
                    value: IrAttachment.browse(message.attachment_ids),
                });
                res.attr("body", ["markup", message.body]);
                res.one("parent_id", "_store_message_fields", {
                    value: MailMessage.browse(message.parent_id),
                });
                res.many("partner_ids", ["avatar_128", "name"], {
                    value: this.env["res.partner"].browse(message.partner_ids),
                });
                res.attr("pinned_at", message.pinned_at);
                res.attr("message_link_preview_ids", message.message_link_preview_ids);
                res.attr("subject", message.subject);
            })
            .as_dict()
    );
    return new Store().add(MailMessage.browse(message_id), "_store_message_fields").as_dict();
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
    const [partner] = this.env["res.partner"].browse(follower.partner_id);
    const subtypeDomain = [
        "&",
        ["hidden", "=", false],
        "|",
        ["res_model", "=", follower.res_model],
        ["res_model", "=", false],
    ];
    if (partner.partner_share) {
        subtypeDomain.unshift("&", ["internal", "=", false]);
    }
    const subtypes = MailMessageSubtype.search(subtypeDomain);
    return {
        store_data: new Store()
            .add(MailMessageSubtype.browse(subtypes), ["name"])
            .add(MailFollowers.browse(follower_id), ["subtype_ids"])
            .as_dict(),
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

registerRoute("mail/thread/update_suggested_recipents", mail_thread_update_suggested_recipients);
async function mail_thread_update_suggested_recipients(request) {
    return [];
}

registerRoute("/mail/store", mail_store);
/** @type {RouteCallback} */
export async function mail_store(request) {
    const args = await parseRequestParams(request);
    return processRequest.call(this, args.fetch_params).as_dict();
}

registerRoute("/discuss/search", search);
/** @type {RouteCallback} */
async function search(request) {
    const { term, limit = 10 } = await parseRequestParams(request);

    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];

    const store = new Store();
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    const base_domain = [
        ...(!term ? [] : [["name", "ilike", term]]),
        ["channel_type", "!=", "chat"],
    ];
    const currentPartnerId = this.env.user?.partner_id;
    const favoriteChannelIds = currentPartnerId
        ? DiscussChannelMember._filter([
              ["partner_id", "=", currentPartnerId],
              ["is_favorite", "=", true],
          ]).map((m) => m.channel_id)
        : [];
    const priority_conditions = [
        [["id", "in", favoriteChannelIds], ...base_domain],
        [["is_member", "=", true], ...base_domain],
        base_domain,
    ];
    const channelIds = new Set();
    let remaining_limit;
    for (const domain of priority_conditions) {
        remaining_limit = limit - channelIds.size;
        if (remaining_limit <= 0) {
            break;
        }
        const partialChannelIds = DiscussChannel.search(
            Domain.and([[["id", "not in", [...channelIds]]], domain]).toList(),
            undefined,
            remaining_limit
        );
        for (const channelId of partialChannelIds) {
            channelIds.add(channelId);
        }
    }
    store.add(DiscussChannel.browse(channelIds), "_store_channel_fields");
    const channelMemberIds = DiscussChannelMember.search([
        ["channel_id", "in", [...channelIds]],
        ["is_self", "=", true],
    ]);
    store.add(DiscussChannelMember.browse(channelMemberIds), (res) => res.attr("is_favorite"));
    ResPartner._search_for_channel_invite(store, term, undefined, limit);
    return store.as_dict();
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
    return new Store()
        .add(thread, "_store_thread_fields", {
            as_thread: true,
            fields_params: { request_list: ["followers", "suggestedRecipients"] },
        })
        .as_dict();
}

registerRoute("/mail/thread/subscribe", mail_thread_subscribe);
/** @type {RouteCallback} */
async function mail_thread_subscribe(request) {
    const { res_model, res_id, partner_ids } = await parseRequestParams(request);
    const thread = this.env[res_model].browse(res_id);
    this.env["mail.thread"].message_subscribe.call(thread, [res_id], partner_ids);
    return new Store()
        .add(thread, "_store_thread_fields", {
            as_thread: true,
            fields_params: { request_list: ["followers", "suggestedRecipients"] },
        })
        .as_dict();
}

function processRequest(fetchParams) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    const store = new Store();
    // Per-request aggregates, batched in a single add once all fetch params have been processed
    // (mirrors the `_process_request_loop` overrides on WebclientController and
    // DiscussChannelWebclientController). The mock env has no mutable request context, so these
    // live on the per-request store instead of `request.env.context`.
    store.request_message_ids = new Set();
    store.add_inbox_fields = false;
    store.add_chatter_fields = false;
    store.request_channel_ids = new Set();
    store.add_channels_last_message = false;
    store.add_channels_last_needaction = false;
    storeHandlerRegistry.execute_for_user(this, store, fetchParams);
    // messages (WebclientController layer)
    if (store.request_message_ids.size) {
        const fields_params = {};
        if (store.add_inbox_fields) {
            fields_params.inbox_fields = true;
        }
        if (store.add_chatter_fields) {
            fields_params.chatter_fields = true;
        }
        store.add(MailMessage.browse([...store.request_message_ids]), "_store_message_fields", {
            fields_params,
        });
    }
    // channels (DiscussChannelWebclientController layer)
    if (store.request_channel_ids.size) {
        const channelIds = [...store.request_channel_ids];
        // is_self is a per-current-user compute only refreshed at create/write in the mock
        DiscussChannelMember.browse(DiscussChannelMember.search([]))._compute_is_self();
        store.add(DiscussChannel.browse(channelIds), "_store_channel_fields");
        const selfMemberIds = channelIds
            .map(
                (channelId) =>
                    DiscussChannelMember._filter([
                        ["channel_id", "=", channelId],
                        ["is_self", "=", true],
                    ])[0]
            )
            .filter(Boolean)
            .map((member) => member.id);
        store.add(DiscussChannelMember.browse(selfMemberIds), ["is_favorite"]);
        if (store.add_channels_last_message) {
            const lastMessageIds = channelIds
                .map(
                    (channelId) =>
                        MailMessage._filter([
                            ["model", "=", "discuss.channel"],
                            ["res_id", "=", channelId],
                        ]).sort((a, b) => b.id - a.id)[0]
                )
                .filter(Boolean)
                .map((message) => message.id);
            store.add(MailMessage.browse(lastMessageIds), "_store_message_fields");
        }
        if (store.add_channels_last_needaction) {
            const lastNeedactionMessageIds = channelIds
                .map((channelId) =>
                    MailMessage._filter([
                        ["model", "=", "discuss.channel"],
                        ["res_id", "=", channelId],
                    ])
                        .sort((a, b) => b.id - a.id)
                        .find((message) => MailMessage._needaction(message))
                )
                .filter(Boolean)
                .map((message) => message.id);
            store.add(MailMessage.browse(lastNeedactionMessageIds), "_store_message_fields");
        }
    }
    return store;
}

export function _resolve_messages(
    store,
    fetch_params,
    { add_to_store = true, filter = () => true } = {}
) {
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    const res = MailMessage._message_fetch(makeKwArgs(fetch_params));
    res.messages = res.messages.filter(filter.bind(this));
    const messageIds = res.messages.map((message) => message.id);
    if (add_to_store) {
        for (const messageId of messageIds) {
            store.request_message_ids.add(messageId);
        }
    }
    store.resolve_data_request((r) => {
        for (const [key, value] of Object.entries(res)) {
            if (key !== "messages") {
                r.attr(key, value);
            }
        }
        // Serialize with the empty field list: messages resolve as ids in the data request; the
        // actual `_store_message_fields` serialization happens once in the post-loop batch.
        r.many("messages", [], { value: MailMessage.browse(messageIds) });
    });
    return res.messages;
}
