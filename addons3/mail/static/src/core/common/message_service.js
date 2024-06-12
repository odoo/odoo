/* @odoo-module */

import { convertBrToLineBreak, prettifyMessageContent } from "@mail/utils/common/format";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

export class MessageService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        this.userService = services.user;
    }

    async edit(
        message,
        body,
        attachments = [],
        { mentionedChannels = [], mentionedPartners = [] } = {}
    ) {
        if (convertBrToLineBreak(message.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
        });
        const messageData = await this.rpc("/mail/message/update_content", {
            attachment_ids: attachments
                .concat(message.attachments)
                .map((attachment) => attachment.id),
            attachment_tokens: attachments
                .concat(message.attachments)
                .map((attachment) => attachment.accessToken),
            body: await prettifyMessageContent(body, validMentions),
            message_id: message.id,
            partner_ids: validMentions?.partners?.map((partner) => partner.id),
        });
        this.store.Message.insert(messageData, { html: true });
        if (!message.isEmpty && this.store.hasLinkPreviewFeature) {
            this.rpc(
                "/mail/link_preview",
                { message_id: message.id, clear: true },
                { silent: true }
            );
        }
    }

    async delete(message) {
        await this.rpc("/mail/message/update_content", {
            attachment_ids: [],
            attachment_tokens: [],
            body: "",
            message_id: message.id,
        });
        if (message.isStarred) {
            this.store.discuss.starred.counter--;
            this.store.discuss.starred.messages.delete(message);
        }
        message.body = "";
        message.attachments = [];
    }

    /**
     * @returns {number}
     */
    getLastMessageId() {
        return Object.values(this.store.Message.records).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
    }

    getNextTemporaryId() {
        return this.getLastMessageId() + 0.01;
    }

    getMentionsFromText(body, { mentionedChannels = [], mentionedPartners = [] } = {}) {
        if (!this.store.user) {
            // mentions are not supported for guests
            return {};
        }
        const validMentions = {};
        const partners = [];
        const threads = [];
        for (const partner of mentionedPartners) {
            const index = body.indexOf(`@${partner.name}`);
            if (index === -1) {
                continue;
            }
            partners.push(partner);
        }
        for (const thread of mentionedChannels) {
            const index = body.indexOf(`#${thread.displayName}`);
            if (index === -1) {
                continue;
            }
            threads.push(thread);
        }
        validMentions.partners = partners;
        validMentions.threads = threads;
        return validMentions;
    }

    async toggleStar(message) {
        await this.orm.silent.call("mail.message", "toggle_message_starred", [[message.id]]);
    }

    async setDone(message) {
        await this.orm.silent.call("mail.message", "set_message_done", [[message.id]]);
    }

    async unfollow(message) {
        if (message.isNeedaction) {
            await this.setDone(message);
        }
        const thread = message.originThread;
        await this.env.services["mail.thread"].removeFollower(thread.selfFollower);
        this.env.services.notification.add(
            _t('You are no longer following "%(thread_name)s".', { thread_name: thread.name }),
            { type: "success" }
        );
    }

    async unstarAll() {
        // apply the change immediately for faster feedback
        this.store.discuss.starred.counter = 0;
        this.store.discuss.starred.messages = [];
        await this.orm.call("mail.message", "unstar_all");
    }

    async react(message, content) {
        await this.rpc(
            "/mail/message/reaction",
            {
                action: "add",
                content,
                message_id: message.id,
            },
            { silent: true }
        );
    }

    async removeReaction(reaction) {
        await this.rpc(
            "/mail/message/reaction",
            {
                action: "remove",
                content: reaction.content,
                message_id: reaction.message.id,
            },
            { silent: true }
        );
    }

    scheduledDateSimple(message) {
        return message.scheduledDate.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: this.userService.lang?.replace("_", "-"),
        });
    }

    dateSimple(message) {
        return message.datetime.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: this.userService.lang?.replace("_", "-"),
        });
    }
}

export const messageService = {
    dependencies: ["mail.store", "rpc", "orm", "user"],
    start(env, services) {
        return new MessageService(env, services);
    },
};

registry.category("services").add("mail.message", messageService);
