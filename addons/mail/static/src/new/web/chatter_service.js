/** @odoo-module */

import { Follower } from "@mail/new/core/follower_model";
import { _t } from "@web/core/l10n/translation";
import { createLocalId } from "../utils/misc";
import { registry } from "@web/core/registry";
import { parseEmail } from "@mail/js/utils";

export class ChatterService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.thread = services["mail.thread"];
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.message = services["mail.message"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.persona = services["mail.persona"];
    }

    /**
     * @param {import("@mail/new/core/thread_model").Thread} thread
     * @param {import("@mail/new/core/thread_model").SuggestedRecipient[]} dataList
     */
    async insertSuggestedRecipients(thread, dataList) {
        const recipients = [];
        for (const data of dataList) {
            const [partner_id, emailInfo, lang, reason] = data;
            const [name, email] = emailInfo && parseEmail(emailInfo);
            recipients.push({
                id: this.store.nextId++,
                name,
                email,
                lang,
                reason,
                persona: partner_id
                    ? this.persona.insert({
                          type: "partner",
                          id: partner_id,
                      })
                    : false,
                checked: partner_id ? true : false,
            });
        }
        thread.suggestedRecipients = recipients;
    }

    /**
     * @param {number} resId
     * @param {string} resModel
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    async fetchData(
        resId,
        resModel,
        requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        if (requestList.includes("messages")) {
            this.thread.fetchNewMessages(this.thread.insert({ model: resModel, id: resId }));
        }
        const result = await this.rpc("/mail/thread/data", {
            request_list: requestList,
            thread_id: resId,
            thread_model: resModel,
        });
        if ("attachments" in result) {
            result["attachments"] = result["attachments"].map((attachment) => ({
                ...attachment,
                originThread: this.thread.insert(attachment.originThread[0][1]),
            }));
        }
        return result;
    }

    getThread(resModel, resId) {
        const localId = createLocalId(resModel, resId);
        if (localId in this.store.threads) {
            if (resId === false) {
                return this.store.threads[localId];
            }
            // to force a reload
            this.store.threads[localId].status = "new";
        }
        const thread = this.thread.insert({
            id: resId,
            model: resModel,
            type: "chatter",
        });
        if (resId === false) {
            const tmpId = `virtual${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.store.self.id },
                body: _t("Creating a new record..."),
                message_type: "notification",
                trackingValues: [],
                res_id: thread.id,
                model: thread.model,
            };
            this.message.insert(tmpData);
        }
        return thread;
    }

    /**
     * @param {import("@mail/new/core/follower_model").Follower} follower
     */
    async removeFollower(follower) {
        await this.orm.call(follower.followedThread.model, "message_unsubscribe", [
            [follower.followedThread.id],
            [follower.partner.id],
        ]);
        const index = follower.followedThread.followers.indexOf(follower);
        if (index !== -1) {
            follower.followedThread.followers.splice(index, 1);
        }
        delete this.store.followers[follower.id];
    }

    /**
     * @param {import("@mail/new/core/follower_model").Data} data
     * @returns {import("@mail/new/core/follower_model").Follower}
     */
    insertFollower(data) {
        let follower = this.store.followers[data.id];
        if (!follower) {
            this.store.followers[data.id] = new Follower();
            follower = this.store.followers[data.id];
        }
        Object.assign(follower, {
            followedThread: data.followedThread,
            id: data.id,
            isActive: data.is_active,
            partner: this.persona.insert({ ...data.partner, type: "partner" }),
            _store: this.store,
        });
        if (!follower.followedThread.followers.includes(follower)) {
            follower.followedThread.followers.push(follower);
        }
        return follower;
    }
}

export const chatterService = {
    dependencies: ["mail.store", "mail.thread", "mail.message", "rpc", "orm", "mail.persona"],
    start(env, services) {
        return new ChatterService(env, services);
    },
};

registry.category("services").add("mail.chatter", chatterService);
