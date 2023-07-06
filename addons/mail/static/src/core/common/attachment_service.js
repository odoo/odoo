/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";

export class AttachmentService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services["rpc"];
    }

    insert(data) {
        if (!("id" in data)) {
            throw new Error("Cannot insert attachment: id is missing in data");
        }
        let attachment = this.store.attachments[data.id];
        if (!attachment) {
            this.store.attachments[data.id] = new Attachment();
            attachment = this.store.attachments[data.id];
            Object.assign(attachment, { _store: this.store, id: data.id });
        }
        this.update(attachment, data);
        return attachment;
    }

    update(attachment, data) {
        assignDefined(attachment, data, [
            "checksum",
            "filename",
            "mimetype",
            "name",
            "type",
            "url",
            "uploading",
            "extension",
            "accessToken",
            "tmpUrl",
            "message",
        ]);
        if (!("extension" in data) && data["name"]) {
            attachment.extension = attachment.name.split(".").pop();
        }
        if (data.originThread !== undefined) {
            const threadData = Array.isArray(data.originThread)
                ? data.originThread[0][1]
                : data.originThread;
            // this prevents cyclic dependencies between mail.thread and mail.attachment
            this.env.bus.trigger("mail.thread/insert", {
                model: threadData.model,
                id: threadData.id,
            });
            attachment.originThreadLocalId = createLocalId(threadData.model, threadData.id);
            const thread = attachment.originThread;
            if (!thread.attachments.includes(attachment)) {
                thread.attachments.push(attachment);
                thread.attachments.sort((a1, a2) => (a1.id < a2.id ? 1 : -1));
            }
        }
    }

    /**
     * Remove the given attachment globally.
     *
     * @param {Attachment} attachment
     */
    remove(attachment) {
        delete this.store.attachments[attachment.id];
        if (attachment.originThread) {
            removeFromArrayWithPredicate(
                attachment.originThread.attachments,
                ({ id }) => id === attachment.id
            );
        }
        for (const message of Object.values(this.store.messages)) {
            removeFromArrayWithPredicate(message.attachments, ({ id }) => id === attachment.id);
            if (message.composer) {
                removeFromArrayWithPredicate(
                    message.composer.attachments,
                    ({ id }) => id === attachment.id
                );
            }
        }
        for (const thread of Object.values(this.store.threads)) {
            removeFromArrayWithPredicate(
                thread.composer.attachments,
                ({ id }) => id === attachment.id
            );
        }
    }

    /**
     * Delete the given attachment on the server as well as removing it
     * globally.
     *
     * @param {Attachment} attachment
     */
    async delete(attachment) {
        this.remove(attachment);
        if (attachment.id > 0) {
            await this.rpc(
                "/mail/attachment/delete",
                assignDefined(
                    { attachment_id: attachment.id },
                    { access_token: attachment.accessToken }
                )
            );
        }
    }
}

export const attachmentService = {
    dependencies: ["mail.store", "rpc"],
    start(env, services) {
        return new AttachmentService(env, services);
    },
};

registry.category("services").add("mail.attachment", attachmentService);
