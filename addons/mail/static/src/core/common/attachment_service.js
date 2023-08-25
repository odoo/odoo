/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";

export class AttachmentService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.rpc = services["rpc"];
    }

    insert(data) {
        if (!("id" in data)) {
            throw new Error("Cannot insert attachment: id is missing in data");
        }
        let attachment = this.store.Attachment.records[data.id];
        if (!attachment) {
            this.store.Attachment.records[data.id] = new Attachment();
            attachment = this.store.Attachment.records[data.id];
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
            this.store.Thread.insert({
                model: threadData.model,
                id: threadData.id,
            });
            attachment.originThreadLocalId = createLocalId(threadData.model, threadData.id);
            const thread = attachment.originThread;
            if (attachment.notIn(thread.attachments)) {
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
        if (attachment.tmpUrl) {
            URL.revokeObjectURL(attachment.tmpUrl);
        }
        delete this.store.Attachment.records[attachment.id];
        if (attachment.originThread) {
            removeFromArrayWithPredicate(attachment.originThread.attachments, (att) =>
                att.eq(attachment)
            );
        }
        for (const message of Object.values(this.store.Message.records)) {
            removeFromArrayWithPredicate(message.attachments, (att) => att.eq(attachment));
            if (message.composer) {
                removeFromArrayWithPredicate(message.composer.attachments, (att) =>
                    att.eq(attachment)
                );
            }
        }
        for (const thread of Object.values(this.store.Thread.records)) {
            removeFromArrayWithPredicate(thread.composer.attachments, (att) => att.eq(attachment));
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
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new AttachmentService(env, services);
    },
};

registry.category("services").add("mail.attachment", attachmentService);
