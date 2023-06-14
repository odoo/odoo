/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { assignDefined, createLocalId } from "@mail/utils/common/misc";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { registry } from "@web/core/registry";

let gEnv;
let rpc;
/** @type {import("@mail/core/common/store_service").Store} */
let store;

/**
 * Delete the given attachment on the server as well as removing it
 * globally.
 *
 * @param {Attachment} attachment
 */
export async function deleteAttachment(attachment) {
    removeAttachment(attachment);
    if (attachment.id > 0) {
        await rpc(
            "/mail/attachment/delete",
            assignDefined(
                { attachment_id: attachment.id },
                { access_token: attachment.accessToken }
            )
        );
    }
}

export function insertAttachment(data) {
    if (!("id" in data)) {
        throw new Error("Cannot insert attachment: id is missing in data");
    }
    let attachment = store.attachments[data.id];
    if (!attachment) {
        store.attachments[data.id] = new Attachment();
        attachment = store.attachments[data.id];
        Object.assign(attachment, { _store: store, id: data.id });
    }
    updateAttachment(attachment, data);
    return attachment;
}

/**
 * Remove the given attachment globally.
 *
 * @param {Attachment} attachment
 */
export function removeAttachment(attachment) {
    delete store.attachments[attachment.id];
    if (attachment.originThread) {
        removeFromArrayWithPredicate(
            attachment.originThread.attachments,
            ({ id }) => id === attachment.id
        );
    }
    for (const message of Object.values(store.messages)) {
        removeFromArrayWithPredicate(message.attachments, ({ id }) => id === attachment.id);
        if (message.composer) {
            removeFromArrayWithPredicate(
                message.composer.attachments,
                ({ id }) => id === attachment.id
            );
        }
    }
    for (const thread of Object.values(store.threads)) {
        removeFromArrayWithPredicate(thread.composer.attachments, ({ id }) => id === attachment.id);
    }
}

export const updateAttachment = makeFnPatchable(function (attachment, data) {
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
        // this prevents cyclic dependencies between insertThread and mail.attachment
        gEnv.bus.trigger("mail.thread/insert", {
            model: threadData.model,
            id: threadData.id,
        });
        attachment.originThreadLocalId = createLocalId(threadData.model, threadData.id);
        if (!attachment.originThread.attachments.includes(attachment)) {
            attachment.originThread.attachments.push(attachment);
        }
    }
});

export class AttachmentService {
    constructor(env, services) {
        gEnv = env;
        store = services["mail.store"];
        rpc = services["rpc"];
    }
}

export const attachmentService = {
    dependencies: ["mail.store", "rpc"],
    start(env, services) {
        return new AttachmentService(env, services);
    },
};

registry.category("services").add("mail.attachment", attachmentService);
