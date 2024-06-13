import { registry } from "@web/core/registry";

/**
 * This routing map is used to redirect the requests made by the livechat to
 * dedicated CORS-allowed routes. Every route expected to be called by the
 * livechat should be added here. Note that this will only be used if the
 * livechat is loaded from a different origin than the Odoo server.
 *
 * @see /im_livechat/embed/cors/boot.js
 */
export const livechatRoutingMap = registry.category("discuss.routing_map");

livechatRoutingMap
    .add("/discuss/channel/messages", "/im_livechat/cors/channel/messages")
    .add("/discuss/channel/notify_typing", "/im_livechat/cors/channel/notify_typing")
    .add("/discuss/channel/mark_as_read", "/im_livechat/cors/channel/mark_as_read")
    .add("/discuss/channel/fold", "/im_livechat/cors/channel/fold")
    .add("/mail/attachment/delete", "/im_livechat/cors/attachment/delete")
    .add("/discuss/channel/ping", "/im_livechat/cors/channel/ping")
    .add("/mail/action", "/im_livechat/cors/action")
    .add("/mail/data", "/im_livechat/cors/data")
    .add("/mail/link_preview", "/im_livechat/cors/link_preview")
    .add("/mail/link_preview/hide", "/im_livechat/cors/link_preview/hide")
    .add("/mail/message/post", "/im_livechat/cors/message/post")
    .add("/mail/message/reaction", "/im_livechat/cors/message/reaction")
    .add("/mail/message/update_content", "/im_livechat/cors/message/update_content")
    .add("/mail/rtc/channel/join_call", "/im_livechat/cors/rtc/channel/join_call")
    .add("/mail/rtc/channel/leave_call", "/im_livechat/cors/rtc/channel/leave_call")
    .add(
        "/mail/rtc/session/notify_call_members",
        "/im_livechat/cors/rtc/session/notify_call_members"
    )
    .add(
        "/mail/rtc/session/update_and_broadcast",
        "/im_livechat/cors/rtc/session/update_and_broadcast"
    )
    .add("/im_livechat/visitor_leave_session", "/im_livechat/cors/visitor_leave_session")
    .add("/im_livechat/get_session", "/im_livechat/cors/get_session")
    .add("/im_livechat/init", "/im_livechat/cors/init")
    .add("/im_livechat/feedback", "/im_livechat/cors/feedback")
    .add("/im_livechat/history", "/im_livechat/cors/history")
    .add("/im_livechat/email_livechat_transcript", "/im_livechat/cors/email_livechat_transcript")
    .add("/chatbot/restart", "/chatbot/cors/restart")
    .add("/chatbot/answer/save", "/chatbot/cors/answer/save")
    .add("/chatbot/step/trigger", "/chatbot/cors/step/trigger")
    .add("/chatbot/step/validate_email", "/chatbot/cors/step/validate_email");
