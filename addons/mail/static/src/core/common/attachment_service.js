import { assignDefined, rpcWithEnv } from "@mail/utils/common/misc";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
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
        rpc = rpcWithEnv(env);
        this.env = env;
        this.store = services["mail.store"];
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
            await rpc(
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
    dependencies: ["mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new AttachmentService(env, services);
    },
};

registry.category("services").add("mail.attachment", attachmentService);
