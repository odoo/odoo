/** @odoo-module */

import { webModels } from "@web/../tests/web_test_helpers";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class IrAttachment extends webModels.IrAttachment {
    /**
     * Simulates `register_as_main_attachment` on `ir.attachment`.
     *
     * @param {number} ids
     * @param {boolean} [force]
     * @param {KwArgs<{ force: boolean }>} [kwargs]
     */
    register_as_main_attachment(ids, force, kwargs = {}) {
        force = kwargs.force ?? force ?? true;
        const [attachment] = this.env["ir.attachment"]._filter([["id", "in", ids]]);
        if (!attachment.res_model) {
            return true; // dummy value for mock server
        }
        if (!this.env[attachment.res_model]._fields.message_main_attachment_id) {
            return true; // dummy value for mock server
        }
        const [record] = this.env[attachment.res_model].search_read([
            ["id", "=", attachment.res_id],
        ]);
        if (force || !record.message_main_attachment_id) {
            this.env[attachment.res_model].write([record.id], {
                message_main_attachment_id: attachment.id,
            });
        }
        return true; // dummy value for mock server
    }

    /**
     * Simulates `_attachment_format` on `ir.attachment`.
     *
     * @param {number} ids
     * @returns {Object}
     */
    _attachmentFormat(ids) {
        return this.read(ids).map((attachment) => {
            const res = {
                create_date: attachment.create_date,
                checksum: attachment.checksum,
                filename: attachment.name,
                id: attachment.id,
                mimetype: attachment.mimetype,
                name: attachment.name,
                size: attachment.file_size,
            };
            res["originThread"] = [["ADD", { id: attachment.res_id, model: attachment.res_model }]];
            const voice = this.env["discuss.voice.metadata"]._filter([
                ["attachment_id", "=", attachment.id],
            ])[0];
            if (voice) {
                res.voice = true;
            }
            return res;
        });
    }
}
