/* @odoo-module */

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

    /**
     * Remove the given attachment globally.
     *
     * @param {import("models").Attachment} attachment
     */
    remove(attachment) {
        if (attachment.tmpUrl) {
            URL.revokeObjectURL(attachment.tmpUrl);
        }
        attachment.delete();
    }

    /**
     * Delete the given attachment on the server as well as removing it
     * globally.
     *
     * @param {Attachment} attachment
     */
    async delete(attachment) {
        if (attachment.id > 0) {
            await this.rpc(
                "/mail/attachment/delete",
                assignDefined(
                    { attachment_id: attachment.id },
                    { access_token: attachment.accessToken }
                )
            );
        }
        this.remove(attachment);
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
