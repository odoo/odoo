/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === "/discuss/channel/attachments") {
            return this._mockRouteDiscussChannelAttachments(
                args.channel_id,
                args.limit,
                args.older_attachment_id
            );
        }
        return super._performRPC(route, args);
    },

    /**
     * Simulates the `/discuss/channel/attachments` route.
     *
     * @param {number} channelId
     * @param {number} [limit=30]
     * @param {number} [olderAttachmentId]
     */
    _mockRouteDiscussChannelAttachments(channelId, limit = 30, olderAttachmentId = null) {
        const attachmentIds = this.models["ir.attachment"].records
            .filter(
                ({ id, res_id, res_model }) =>
                    res_id === channelId &&
                    res_model === "discuss.channel" &&
                    (!olderAttachmentId || id < olderAttachmentId)
            )
            .sort()
            .slice(0, limit)
            .map(({ id }) => id);
        return this._mockIrAttachment_attachmentFormat(attachmentIds);
    },
});
