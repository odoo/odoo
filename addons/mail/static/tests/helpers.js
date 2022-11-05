/** @odoo-module **/

import { messagingService } from "@mail/messaging_service";
import { ormService } from "@web/core/orm_service";
import { EventBus } from "@odoo/owl";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";

export function makeMessagingEnv(rpc) {
    const user = {
        context: { uid: 2 },
        partnerId: 3,
    };
    const ui = {
        get activeElement() {
            return document.activeElement;
        },
    };
    const router = { current: { hash: { active_id: false } }, pushState() {} };
    const bus_service = new EventBus();
    const env = {
        _t: (s) => s,
        services: { rpc, user, router, bus_service, action: {}, dialog: {}, ui, popover: {} },
    };
    const hotkey = hotkeyService.start(env, { ui });
    env.services.hotkey = hotkey;
    const orm = ormService.start(env, { rpc, user });
    env.services.orm = orm;

    const messaging = messagingService.start(env, { rpc, orm, user, router, bus_service });
    env.services['mail.messaging'] = messaging;
    return env;
}

export class MessagingServer {
    channels = [];
    chats = [];
    messages = [];
    partners = [{ id: 3, name: "Mitchell Admin" }];
    nextChannelId = 123;
    nextMessageId = 456;

    addChannel(id, name, description) {
        const channel = {
            id,
            name,
            last_message_id: 9,
            seen_message_id: 1,
            description,
            channel: {
                channel_type: "channel",
                message_needaction_counter: 0,
                group_based_subscription: true,
                create_uid: 1,
            },
        };
        this.channels.push(channel);
        return channel;
    }
    addChat(id, name, partnerId) {
        const chatChannel = {
            id,
            name,
            last_message_id: false,
            seen_message_id: false,
            description: false,
            seen_partners_info: [{ partner_id: partnerId }],
            channel: {
                avatarCacheKey: false,
                channel_type: "chat",
                channelMembers: [["insert", [{ persona: { partner: { id: partnerId, name } } }]]],
            },
        };
        this.chats.push(chatChannel);
        return chatChannel;
    }

    /**
     *
     * @param {'commnent'} type
     */
    addMessage(type, id, authorId, body, date) {
        const author = this.partners.find((p) => p.id === authorId);
        if (!author) {
            throw new Error("missing author");
        }
        const message = {
            id,
            body,
            author,
            date,
            message_type: type,
        };
        this.messages[id] = message;
        return message;
    }

    addPartner(id, name) {
        const partner = { id, name };
        this.partners.push(partner);
        return partner;
    }

    async rpc(route, params) {
        const result = this.handleRequest(route, params);
        if (QUnit.config.debug) {
            console.groupCollapsed(`rpc ${route}`);
            console.log(`Request parameters:`, params);
            console.log(`Response:`, result);
            console.trace();
            console.groupEnd();
        }
        return JSON.parse(JSON.stringify(result));
    }

    handleRequest(route, params) {
        switch (route) {
            case "/mail/init_messaging":
                return {
                    current_partner: { id: 3, name: "Mitchell Admin" },
                    partner_root: { id: 2, name: "OdooBot" },
                    channels: this.channels,
                    current_user_settings: {
                        is_discuss_sidebar_category_channel_open: true,
                        is_discuss_sidebar_category_chat_open: true,
                    },
                    internalUserGroupId: 1,
                };
            case "/mail/inbox/messages":
                return [];
            case "/mail/channel/messages":
                return [];
            case "/mail/message/post":
                return this.addMessage("comment", this.nextMessageId++, 3, params.post_data.body);
            case "/web/dataset/call_kw/mail.channel/search_read":
                const nameSearch = params.kwargs.domain[1][2];
                return this.channels.filter((channel) => channel.name.includes(nameSearch));
            case "/web/dataset/call_kw/mail.channel/channel_create":
                return this.addChannel(this.nextChannelId++, params.args[0]);
            case "/web/dataset/call_kw/res.partner/im_search":
                const searchStr = params.args[0];
                return this.partners.filter((p) => p.name.includes(searchStr));
            case "/web/dataset/call_kw/mail.channel/channel_get":
                // we assume this is for a chat request
                const partnerId = params.kwargs.partners_to[0];
                const chat = this.chats.find(
                    (c) => c.seen_partners_info[0].partner_id === partnerId
                );
                if (chat) {
                    return chat;
                }
                return this.addChat(this.nextChannelId++, "some name", partnerId);
            default:
                throw new Error("Unhandled route: " + route);
        }
    }
}
