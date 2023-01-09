/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/models/ir_attachment", {
    async _performRPC(route, args) {
        if (args.model === "ir.attachment" && args.method === "register_as_main_attachment") {
            const ids = args.args[0];
            return this._mockIrAttachmentRegisterAsMainAttachment(ids);
        }
        return this._super(route, args);
    },
    /**
     * Simulates `_attachment_format` on `ir.attachment`.
     *
     * @private
     * @param {integer} ids
     * @returns {Object}
     */
    _mockIrAttachment_attachmentFormat(ids) {
        const attachments = this.mockRead("ir.attachment", [ids]);
        return attachments.map((attachment) => {
            const res = {
                checksum: attachment.checksum,
                filename: attachment.name,
                id: attachment.id,
                mimetype: attachment.mimetype,
                name: attachment.name,
            };
            res["originThread"] = [
                [
                    "insert",
                    {
                        id: attachment.res_id,
                        model: attachment.res_model,
                    },
                ],
            ];
            return res;
        });
    },
    /**
     * Simulates `register_as_main_attachment` on `ir.attachment`.
     *
     * @private
     * @param {integer} ids
     * @param {boolean} [force=true]
     * @returns {boolean} dummy value for mock server
     */
    _mockIrAttachmentRegisterAsMainAttachment(ids, force = true) {
        const [attachment] = this.getRecords("ir.attachment", [["id", "in", ids]]);
        if (!attachment.res_model) {
            return true; // dummy value for mock server
        }
        if (!this.models[attachment.res_model].fields["message_main_attachment_id"]) {
            return true; // dummy value for mock server
        }
        const [record] = this.pyEnv[attachment.res_model].searchRead([
            ["id", "=", attachment.res_id],
        ]);
        if (force || !record.message_main_attachment_id) {
            this.pyEnv[attachment.res_model].write([record.id], {
                message_main_attachment_id: attachment.id,
            });
        }
        return true; // dummy value for mock server
    },
});
