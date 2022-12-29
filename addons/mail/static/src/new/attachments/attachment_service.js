/** @odoo-module */

import { Attachment } from "./attachment_model";
import { assignDefined, createLocalId } from "../utils/misc";
import { registry } from "@web/core/registry";
import { removeFromArrayWithPredicate } from "../utils/arrays";

export class AttachmentService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services["rpc"];
    }

    insert(data) {
        if (!("id" in data)) {
            throw new Error("Cannot insert attachment: id is missing in data");
        }
        if (data.id in this.store.attachments) {
            const attachment = this.store.attachments[data.id];
            this.update(attachment, data);
            return attachment;
        }
        const attachment = (this.store.attachments[data.id] = new Attachment());
        Object.assign(attachment, { _store: this.store, id: data.id });
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
        ]);
        if (!("extension" in data) && data["name"]) {
            attachment.extension = attachment.name.split(".").pop();
        }
        if (data.originThread !== undefined) {
            const threadData = Array.isArray(data.originThread)
                ? data.originThread[0][1]
                : data.originThread;
            // FIXME this prevents cyclic dependencies between mail.thread and mail.message
            this.env.bus.trigger("MESSAGE-SERVICE:INSERT_THREAD", {
                model: threadData.model,
                id: threadData.id,
            });
            attachment.originThreadLocalId = createLocalId(threadData.model, threadData.id);
            const originThread = this.store.threads[attachment.originThreadLocalId];
            if (!originThread.attachments.some((a) => a.id === attachment.id)) {
                originThread.attachments.push(attachment);
            }
        }
    }

    /**
     * @param {Attachment} attachment
     */
    async delete(attachment) {
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
        if (attachment.id > 0) {
            await this.rpc("/mail/attachment/delete", {
                attachment_id: attachment.id,
            });
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
