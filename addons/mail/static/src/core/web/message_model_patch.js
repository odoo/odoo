import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @typedef {import('models').Models} M */

/**
 * @template {new (...args: any[]) => any} C
 * @template {Record<string, any>} T
 * @param {C} Model - The original or partially patched target class
 * @param {T & ThisType<M[C["_name"]]>} obj
 * @returns {T}
 */
function patchModel(Model, obj) {
    patch(Model.prototype, obj);
    return obj;
}

export const messagePatch1 = patchModel(Message, {
    get canReplyAll() {
        return this.canForward && !this.isNote && !this.isEmpty;
    },
    get canForward() {
        if (!this.thread || this.isEmpty) {
            return false;
        }
        return (
            !this.thread.channel &&
            ["comment", "email", "email_outgoing"].includes(this.message_type)
        );
    },
});
