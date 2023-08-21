/* @odoo-module */

import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { assignDefined } from "@mail/utils/common/misc";

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
        return this.store.Attachment.insert(data);
    }

    update(attachment, data) {
        return this.store.Attachment.update(attachment, data);
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
        for (const message of Object.values(this.store.messages)) {
            removeFromArrayWithPredicate(message.attachments, (att) => att.eq(attachment));
            if (message.composer) {
                removeFromArrayWithPredicate(message.composer.attachments, (att) =>
                    att.eq(attachment)
                );
            }
        }
        for (const thread of Object.values(this.store.threads)) {
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
