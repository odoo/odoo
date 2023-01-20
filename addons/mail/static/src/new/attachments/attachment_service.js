/** @odoo-module */

import { Attachment } from "./attachment_model";
import { assignDefined, createLocalId } from "../utils/misc";
import { registry } from "@web/core/registry";

export class AttachmentService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
    }

    insert(data) {
        const attachment = new Attachment();
        attachment._store = this.store;
        assignDefined(attachment, data, [
            "id",
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
        if (!("extension" in data) && "name" in data) {
            attachment.extension = attachment.name.split(".").pop();
        }
        if ("originThread" in data) {
            const threadData = Array.isArray(data.originThread)
                ? data.originThread[0][1]
                : data.originThread;
            attachment.originThreadLocalId = createLocalId(threadData.model, threadData.id);
        }
        return attachment;
    }
}

export const attachmentService = {
    dependencies: ["mail.store"],
    start(env, services) {
        return new AttachmentService(env, services);
    },
};

registry.category("services").add("mail.attachment", attachmentService);
