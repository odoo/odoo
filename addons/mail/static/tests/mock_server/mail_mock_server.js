/** @odoo-module */

import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

/**
 * @template [T={}]
 * @typedef {import("@web/../tests/web_test_helpers").RouteCallback<T>} RouteCallback
 */

const { DateTime } = luxon;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Request} request
 */
const parseRequestParams = async (request) => {
    const response = await request.json();
    return response.params;
};

// RPC handlers

/** @type {RouteCallback}} */
async function attachmentUpload(request) {
    const { body } = await parseRequestParams(request);
    const ufile = body.get("ufile");
    const is_pending = body.get("is_pending") === "true";
    const model = is_pending ? "mail.compose.message" : body.get("thread_model");
    const id = is_pending ? 0 : parseInt(body.get("thread_id"));
    const attachmentId = this.env["ir.attachment"].create({
        // datas,
        mimetype: ufile.type,
        name: ufile.name,
        res_id: id,
        res_model: model,
    });
    if (body.get("voice")) {
        this.env["discuss.voice.metadata"].create({ attachment_id: attachmentId });
    }
    return this.env["ir.attachment"]._attachmentFormat([attachmentId])[0];
}

/** @type {RouteCallback} */
async function attachmentDelete(request) {
    const { attachment_id } = await parseRequestParams(request);
    this.env["bus.bus"]._sendone(this.env.partner, "ir.attachment/delete", {
        id: attachment_id,
    });
    return this.env["ir.attachment"].unlink([attachment_id]);
}

/** @type {RouteCallback} */
async function channelAttachments(request) {
    const { channel_id, limit, older_attachment_id } = await parseRequestParams(request);
    const Attachment = this.env["ir.attachment"];
    const attachmentIds = Attachment.filter(
        ({ id, res_id, res_model }) =>
            res_id === channel_id &&
            res_model === "discuss.channel" &&
            (!older_attachment_id || id < older_attachment_id)
    )
        .sort()
        .slice(0, limit)
        .map(({ id }) => id);
    return Attachment._attachmentFormat(attachmentIds);
}

/** @type {RouteCallback} */
async function channelJoinCall(request) {
    const { channel_id } = await parseRequestParams(request);
    const memberOfCurrentUser =
        this.env["discuss.channel.member"]._getAsSudoFromContext(channel_id);
    const sessionId = this.env["discuss.channel.rtc.session"].create({
        channel_member_id: memberOfCurrentUser.id,
        channel_id, // on the server, this is a related field from channel_member_id and not explicitly set
        guest_id: memberOfCurrentUser.guest_id[0],
        partner_id: memberOfCurrentUser.partner_id[0],
    });
    const channelMembers = this.env["discuss.channel.member"]._filter([
        ["channel_id", "=", channel_id],
    ]);
    const rtcSessions = this.env["discuss.channel.rtc.session"]._filter([
        ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
    ]);
    return {
        iceServers: false,
        rtcSessions: [
            ["ADD", rtcSessions.map((rtcSession) => this._mailRtcSessionFormat(rtcSession.id))],
        ],
        sessionId: sessionId,
    };
}

/** @type {RouteCallback} */
async function channelLeaveCall(request) {
    const { channel_id } = await parseRequestParams(request);
    const channelMembers = this.env["discuss.channel.member"]._filter([
        ["channel_id", "=", channel_id],
    ]);
    const rtcSessions = this.env["discuss.channel.rtc.session"]._filter([
        ["channel_member_id", "in", channelMembers.map((channelMember) => channelMember.id)],
    ]);
    const notifications = [];
    const channelInfo = this._mailRtcSessionFormatByChannel(
        rtcSessions.map((rtcSession) => rtcSession.id)
    );
    for (const [channelId, sessionsData] of Object.entries(channelInfo)) {
        const channel = this.env["discuss.channel"].search_read([
            ["id", "=", parseInt(channelId)],
        ])[0];
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
            ? this.env["mail.guest"].search_read([["id", "=", rtcSession.guest_id]])[0]
            : this.env["res.partner"].search_read([["id", "=", rtcSession.partner_id]])[0];
        notifications.push([
            target,
            "discuss.channel.rtc.session/ended",
            { sessionId: rtcSession.id },
        ]);
    }
    this.env["bus.bus"]._sendmany(notifications);
}

/** @type {RouteCallback} */
async function channelFold(request) {
    const { channel_id, state, state_count } = await parseRequestParams(request);
    const memberOfCurrentUser =
        this.env["discuss.channel.member"]._getAsSudoFromContext(channel_id);
    return this.env["discuss.channel.member"]._channelFold(
        memberOfCurrentUser.id,
        state,
        state_count
    );
}

/** @type {RouteCallback} */
async function channelMembers(request) {
    const { channel_id, known_member_ids } = await parseRequestParams(request);
    return this.env["discuss.channel"]._loadOlderMembers([channel_id], known_member_ids);
}

/** @type {RouteCallback} */
async function channelMessages(request) {
    const { after, around, before, channel_id, limit, search_term } = await parseRequestParams(
        request
    );
    const domain = [
        ["res_id", "=", channel_id],
        ["model", "=", "discuss.channel"],
        ["message_type", "!=", "user_notification"],
    ];
    const res = this.env["mail.message"]._messageFetch(
        domain,
        search_term,
        before,
        after,
        around,
        limit
    );
    if (!around) {
        this.env["mail.message"].set_message_done(res.messages.map((message) => message.id));
    }
    return {
        ...res,
        messages: this.env["mail.message"].message_format(
            res.messages.map((message) => message.id)
        ),
    };
}

/** @type {RouteCallback} */
async function channelMute(request) {
    const { channel_id, minutes } = await parseRequestParams(request);
    const member = this.env["discuss.channel.member"]._getAsSudoFromContext(channel_id);
    let mute_until_dt;
    if (minutes === -1) {
        mute_until_dt = serializeDateTime(DateTime.fromISO("9999-12-31T23:59:59"));
    } else if (minutes) {
        mute_until_dt = serializeDateTime(DateTime.now().plus({ minutes }));
    } else {
        mute_until_dt = false;
    }
    this.env["discuss.channel.member"].write([member.id], { mute_until_dt });
    const channel_data = {
        id: member.channel_id[0],
        model: "discuss.channel",
        mute_until_dt,
    };
    this.env["bus.bus"]._sendone(this.env.partner, "mail.record/insert", {
        MailThread: channel_data,
    });
    return "dummy";
}

/** @type {RouteCallback} */
async function channelNotifyTyping(request) {
    const { channel_id, is_typing } = await parseRequestParams(request);
    const memberOfCurrentUser =
        this.env["discuss.channel.member"]._getAsSudoFromContext(channel_id);
    if (!memberOfCurrentUser) {
        return;
    }
    this.env["discuss.channel.member"].notify_typing([memberOfCurrentUser.id], is_typing);
}

/** @type {RouteCallback} */
async function channelPing(request) {}

/** @type {RouteCallback} */
async function channelPinnedMessages(request) {
    const { channel_id } = await parseRequestParams(request);
    const messageIds = this.env["mail.message"].search([
        ["model", "=", "discuss.channel"],
        ["res_id", "=", channel_id],
        ["pinned_at", "!=", false],
    ]);
    return this.env["mail.message"].message_format(messageIds);
}

/** @type {RouteCallback} */
async function channelSetLastSeenMessage(request) {
    const { channel_id, last_message_id } = await parseRequestParams(request);
    return this.env["discuss.channel"]._channelSeen([channel_id], last_message_id);
}

/** @type {RouteCallback} */
async function channels(request) {
    const Channel = this.env["discuss.channel"];
    const Message = this.env["mail.message"];
    const channels = Channel.get_channels_as_member();
    return {
        Message: channels
            .map((channel) => {
                const channelMessages = Message._filter([
                    ["model", "=", "discuss.channel"],
                    ["res_id", "=", channel.id],
                ]);
                const lastMessage = channelMessages.reduce((lastMessage, message) => {
                    if (message.id > lastMessage.id) {
                        return message;
                    }
                    return lastMessage;
                }, channelMessages[0]);
                return lastMessage ? Message.message_format([lastMessage.id])[0] : false;
            })
            .filter((lastMessage) => lastMessage),
        Thread: Channel.channel_info(channels.map((channel) => channel.id)),
    };
}

/** @type {RouteCallback} */
async function gifFavorites(request) {
    return [[]];
}

/** @type {RouteCallback} */
async function historyMessages(request) {
    const { after, before, limit, search_term } = await parseRequestParams(request);
    const domain = [["needaction", "=", false]];
    const res = this.env["mail.message"]._messageFetch(
        domain,
        search_term,
        before,
        after,
        false,
        limit
    );
    const messagesWithNotification = res.messages.filter((message) => {
        const notifs = this.env["mail.notification"].search_read([
            ["mail_message_id", "=", message.id],
            ["is_read", "=", true],
            ["res_partner_id", "=", this.env.partner_id],
        ]);
        return notifs.length > 0;
    });

    return {
        ...res,
        messages: this.env["mail.message"].message_format(
            messagesWithNotification.map((message) => message.id)
        ),
    };
}

/** @type {RouteCallback} */
async function inboxMessages(request) {
    const { after, around, before, limit, search_term } = await parseRequestParams(request);
    const domain = [["needaction", "=", true]];
    const res = this.env["mail.message"]._messageFetch(
        domain,
        search_term,
        before,
        after,
        around,
        limit
    );
    return {
        ...res,
        messages: this.env["mail.message"]._messageFormatPersonalize(
            res.messages.map((message) => message.id)
        ),
    };
}

/** @type {RouteCallback} */
async function initMessaging(request) {
    if (this.env["mail.guest"]._getGuestFromContext() && this.env.user?.is_public) {
        return this.env["mail.guest"]._initMessaging();
    }
    return this.env["res.users"]._initMessaging([this.env.uid]);
}

/** @type {RouteCallback} */
async function linkPreview(request) {
    const { clear, message_id } = await parseRequestParams(request);
    const linkPreviews = [];
    const [message] = this.env["mail.message"].search_read([["id", "=", message_id]]);
    const LinkPreview = this.env["mail.link.preview"];
    if (message.body.includes("https://make-link-preview.com")) {
        if (clear) {
            const [linkPreview] = LinkPreview.search_read([["message_id", "=", message_id]]);
            this.env["bus.bus"]._sendone(
                this.env["mail.message"]._busNotificationTarget(linkPreview.message_id),
                "mail.link.preview/delete",
                {
                    id: linkPreview.id,
                    message_id: linkPreview.message_id,
                }
            );
        }

        const linkPreviewId = LinkPreview.create({
            message_id: message.id,
            og_description: "test description",
            og_title: "Article title",
            og_type: "article",
            source_url: "https://make-link-preview.com",
        });
        const [linkPreview] = LinkPreview.search_read([["id", "=", linkPreviewId]]);
        linkPreviews.push(LinkPreview._linkPreviewFormat(linkPreview));
        this.env["bus.bus"]._sendone(
            this.env["mail.message"]._busNotificationTarget(message_id),
            "mail.record/insert",
            { LinkPreview: linkPreviews }
        );
    }
}

/** @type {RouteCallback} */
async function linkPreviewDelete(request) {
    const { link_preview_ids } = await parseRequestParams(request);
    const linkPreviews = this.env["mail.link.preview"].search_read([
        ["id", "in", link_preview_ids],
    ]);
    for (const linkPreview of linkPreviews) {
        this.env["bus.bus"]._sendone(
            this.env["mail.message"]._busNotificationTarget(linkPreview.message_id[0]),
            "mail.link.preview/delete",
            {
                id: linkPreview.id,
                message_id: linkPreview.message_id[0],
            }
        );
    }
    return link_preview_ids;
}

/** @type {RouteCallback} */
async function loadMessageFailures(request) {
    return this.env["res.partner"]._messageFetchFailed(this.env.partner_id);
}

/** @type {RouteCallback} */
async function messagePost(request) {
    const { context, post_data, thread_id, thread_model } = await parseRequestParams(request);
    const finalData = {};
    for (const allowedField of [
        "attachment_ids",
        "body",
        "message_type",
        "partner_ids",
        "subtype_xmlid",
        "parent_id",
    ]) {
        if (post_data[allowedField] !== undefined) {
            finalData[allowedField] = post_data[allowedField];
        }
    }
    const kwargs = { ...finalData, context };
    if (thread_model === "discuss.channel") {
        return this.env["discuss.channel"].message_post(thread_id, null, kwargs);
    }
    return this.env["mail.thread"].message_post([thread_id], {
        ...kwargs,
        model: thread_model,
    });
}

/** @type {RouteCallback} */
async function messageReaction(request) {
    const { action, content, message_id } = await parseRequestParams(request);
    return this.env["mail.message"]._messageReaction(message_id, content, action);
}

/** @type {RouteCallback} */
async function messageUpdateContent(request) {
    const { attachment_ids, body, message_id } = await parseRequestParams(request);
    this.env["mail.message"].write([message_id], {
        body,
        attachment_ids,
    });
    this.env["bus.bus"]._sendone(
        this.env["mail.message"]._busNotificationTarget(message_id),
        "mail.record/insert",
        {
            MailMessage: {
                id: message_id,
                body,
                attachments: this.env["ir.attachment"]._attachmentFormat(attachment_ids),
            },
        }
    );
    return this.env["mail.message"].message_format([message_id])[0];
}

/** @type {RouteCallback} */
async function partnerAvatar128(request, { cid, pid }) {
    return [cid, pid];
}

/** @type {RouteCallback} */
async function partnerFromEmail(request) {
    const { emails } = await parseRequestParams(request);
    const partners = emails.map(
        (email) => this.env["res.partner"].search([["email", "=", email]])[0]
    );
    for (const index in partners) {
        if (!partners[index]) {
            partners[index] = this.env["res.partner"].create({
                email: emails[index],
                name: emails[index],
            });
        }
    }
    return partners.map((partner_id) => {
        const partner = this.env["res.partner"]._filter([["id", "=", partner_id]])[0];
        return { id: partner_id, name: partner.name, email: partner.email };
    });
}

/** @type {RouteCallback} */
async function readSubscriptionData(request) {
    const { follower_id } = await parseRequestParams(request);
    const follower = this.env["mail.followers"]._filter([["id", "=", follower_id]])[0];
    const subtypes = this.env["mail.message.subtype"]._filter([
        "&",
        ["hidden", "=", false],
        "|",
        ["res_model", "=", follower.res_model],
        ["res_model", "=", false],
    ]);
    const subtypes_list = subtypes.map((subtype) => {
        const parent = this.env["mail.message.subtype"]._filter([
            ["id", "=", subtype.parent_id],
        ])[0];
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

/** @type {RouteCallback} */
async function sessionUpdateAndBroadcast(request) {}

/** @type {RouteCallback} */
async function starredMessages(request) {
    const { after, before, limit, search_term } = await parseRequestParams(request);
    const domain = [["starred_partner_ids", "in", [this.env.partner_id]]];
    const res = this.env["mail.message"]._messageFetch(
        domain,
        search_term,
        before,
        after,
        false,
        limit
    );
    return {
        ...res,
        messages: this.env["mail.message"].message_format(
            res.messages.map((message) => message.id)
        ),
    };
}

/** @type {RouteCallback} */
async function threadData(request) {
    const { request_list, thread_model, thread_id } = await parseRequestParams(request);
    const res = {
        hasWriteAccess: true, // mimic user with write access by default
        hasReadAccess: true,
    };
    const thread = this.env[thread_model].search_read([["id", "=", thread_id]])[0];
    if (!thread) {
        res["hasReadAccess"] = false;
        return res;
    }
    res["canPostOnReadonly"] = thread_model === "discuss.channel"; // model that have attr _mail_post_access='read'
    if (request_list.includes("activities")) {
        const activities = this.env["mail.activity"].search_read([
            ["id", "in", thread.activity_ids || []],
        ]);
        res["activities"] = this._mockMailActivityActivityFormat(
            activities.map((activity) => activity.id)
        );
    }
    if (request_list.includes("attachments")) {
        const attachments = this.env["ir.attachment"].search_read([
            ["res_id", "=", thread.id],
            ["res_model", "=", thread_model],
        ]); // order not done for simplicity
        res["attachments"] = this.env["ir.attachment"]._attachmentFormat(
            attachments.map((attachment) => attachment.id)
        );
        // Specific implementation of mail.thread.main.attachment
        if (this.env[thread_model]._fields.message_main_attachment_id) {
            res["mainAttachment"] = thread.message_main_attachment_id
                ? { id: thread.message_main_attachment_id[0] }
                : false;
        }
    }
    if (request_list.includes("followers")) {
        const domain = [
            ["res_id", "=", thread.id],
            ["res_model", "=", thread_model],
        ];
        res["followersCount"] = (thread.message_follower_ids || []).length;
        const selfFollower = this.env["mail.followers"].search_read(
            domain.concat([["partner_id", "=", this.env.partner_id]])
        )[0];
        res["selfFollower"] = selfFollower
            ? this.env["mail.followers"]._formatForChatter(selfFollower.id)[0]
            : false;
        res["followers"] = this._mockMailThreadMessageGetFollowers(thread_model, [thread_id]);
        res["recipientsCount"] = (thread.message_follower_ids || []).length - 1;
        res["recipients"] = this._mockMailThreadMessageGetFollowers(
            thread_model,
            [thread_id],
            undefined,
            100,
            { filter_recipients: true }
        );
    }
    if (request_list.includes("suggestedRecipients")) {
        res["suggestedRecipients"] = this.env["mail.thread"]._messageGetSuggestedRecipients(
            thread_model,
            [thread.id]
        )[thread_id];
    }
    return res;
}

/** @type {RouteCallback} */
async function threadMessages(request) {
    const { after, around, before, limit, search_term, thread_id, thread_model } =
        await parseRequestParams(request);
    const domain = [
        ["res_id", "=", thread_id],
        ["model", "=", thread_model],
        ["message_type", "!=", "user_notification"],
    ];
    const res = this.env["mail.message"]._messageFetch(
        domain,
        search_term,
        before,
        after,
        around,
        limit
    );
    this._mockMailMessageSetMessageDone(res.messages.map((message) => message.id));
    return {
        ...res,
        messages: this.env["mail.message"].message_format(
            res.messages.map((message) => message.id)
        ),
    };
}

//
registry
    .category("mock_rpc")
    .add("/discuss/channel/attachments", channelAttachments)
    .add("/discuss/channel/fold", channelFold)
    .add("/discuss/channel/members", channelMembers)
    .add("/discuss/channel/messages", channelMessages)
    .add("/discuss/channel/mute", channelMute)
    .add("/discuss/channel/:cid/partner/:pid/avatar_128", partnerAvatar128)
    .add("/discuss/channel/notify_typing", channelNotifyTyping)
    .add("/discuss/channel/ping", channelPing)
    .add("/discuss/channel/pinned_messages", channelPinnedMessages)
    .add("/discuss/channel/set_last_seen_message", channelSetLastSeenMessage)
    .add("/discuss/channels", channels)
    .add("/discuss/gif/favorites", gifFavorites)
    .add("/mail/attachment/upload", attachmentUpload)
    .add("/mail/attachment/delete", attachmentDelete)
    .add("/mail/history/messages", historyMessages)
    .add("/mail/inbox/messages", inboxMessages)
    .add("/mail/init_messaging", initMessaging)
    .add("/mail/link_preview", linkPreview)
    .add("/mail/link_preview/delete", linkPreviewDelete)
    .add("/mail/load_message_failures", loadMessageFailures)
    .add("/mail/message/post", messagePost)
    .add("/mail/message/reaction", messageReaction)
    .add("/mail/message/update_content", messageUpdateContent)
    .add("/mail/partner/from_email", partnerFromEmail)
    .add("/mail/read_subscription_data", readSubscriptionData)
    .add("/mail/rtc/channel/join_call", channelJoinCall)
    .add("/mail/rtc/channel/leave_call", channelLeaveCall)
    .add("/mail/rtc/session/update_and_broadcast", sessionUpdateAndBroadcast)
    .add("/mail/starred/messages", starredMessages)
    .add("/mail/thread/data", threadData)
    .add("/mail/thread/messages", threadMessages);
