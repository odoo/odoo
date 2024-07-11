/* @odoo-module */

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
    .add(
        "/discuss/channel/set_last_seen_message",
        "/im_livechat/cors/channel/set_last_seen_message"
    )
    .add("/mail/attachment/delete", "/im_livechat/cors/attachment/delete")
    .add("/discuss/channel/ping", "/im_livechat/cors/channel/ping")
    .add("/mail/init_messaging", "/im_livechat/cors/init_messaging")
    .add("/mail/link_preview", "/im_livechat/cors/link_preview")
    .add("/mail/link_preview/delete", "/im_livechat/cors/link_preview/delete")
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
    .add("/im_livechat/get_session", "/im_livechat/cors/get_session");
