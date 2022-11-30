/** @odoo-module **/

import { Composer } from "@mail/new/common/models/composer_model";
import { Partner } from "@mail/new/common/models/partner_model";

export class Thread {
    static insert(state, data) {
        if (data.id in state.threads) {
            return state.threads[data.id];
        }
        const thread = new Thread(data);
        thread.composer = Composer.insert(state, { threadId: thread.id });
        if (thread.type === "channel") {
            state.discuss.channels.threads.push(thread.id);
            const avatarCacheKey = data.serverData.channel.avatarCacheKey;
            thread.imgUrl = `/web/image/mail.channel/${data.id}/avatar_128?unique=${avatarCacheKey}`;
        }
        if (thread.type === "chat") {
            thread.is_pinned = data.serverData.is_pinned;
            state.discuss.chats.threads.push(thread.id);
            if (data.serverData) {
                const avatarCacheKey = data.serverData.channel.avatarCacheKey;
                for (const elem of data.serverData.channel.channelMembers[0][1]) {
                    Partner.insert(state, {
                        id: elem.persona.partner.id,
                        name: elem.persona.partner.name,
                    });
                    if (
                        elem.persona.partner.id !== state.user.partnerId ||
                        (data.serverData.channel.channelMembers[0][1].length === 1 &&
                            elem.persona.partner.id === state.user.partnerId)
                    ) {
                        thread.chatPartnerId = elem.persona.partner.id;
                        thread.name = state.partners[elem.persona.partner.id].name;
                    }
                }
                thread.imgUrl = `/web/image/res.partner/${thread.chatPartnerId}/avatar_128?unique=${avatarCacheKey}`;
            }
        }

        state.threads[thread.id] = thread;
        // return reactive version
        return state.threads[thread.id];
    }

    constructor(data) {
        const { id, name, type } = data;
        Object.assign(this, {
            hasWriteAccess: data.serverData && data.serverData.hasWriteAccess,
            id,
            name,
            type,
            counter: 0,
            isUnread: false,
            icon: false,
            loadMore: false,
            description: false,
            status: "new", // 'new', 'loading', 'ready'
            imgUrl: false,
            messages: [], // list of ids
            chatPartnerId: false,
            isAdmin: false,
            canLeave: data.canLeave || false,
            isDescriptionChangeable: ["channel", "group"].includes(type),
            isRenameable: ["chat", "channel", "group"].includes(type),
            composer: null,
            serverLastSeenMsgByCurrentUser: data.serverData
                ? data.serverData.seen_message_id
                : null,
        });
        for (const key in data) {
            this[key] = data[key];
        }
    }
}
