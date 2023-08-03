/* @odoo-module */

import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { assignDefined } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";

export class AttachmentService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services["rpc"];
    }

    /**
     * Remove the given attachment globally.
     *
     * @param {Attachment} attachment
     */
    remove(attachment) {
        delete this.store.Attachment.records[attachment.id];
        if (attachment.originThread) {
            removeFromArrayWithPredicate(
                attachment.originThread.attachments,
                ({ id }) => id === attachment.id
            );
        }
        for (const message of Object.values(this.store.Message.records)) {
            removeFromArrayWithPredicate(message.attachments, ({ id }) => id === attachment.id);
            if (message.composer) {
                removeFromArrayWithPredicate(
                    message.composer.attachments,
                    ({ id }) => id === attachment.id
                );
            }
        }
        for (const thread of Object.values(this.store.Thread.records)) {
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
