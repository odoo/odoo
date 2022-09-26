/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/models/mail_link_preview', {
    /**
     * Simulates the `_link_preview_format` method of `mail.link.preview`.
     *
     * @private
     * @param {object} linkPreview
     */
    _mockMailLinkPreviewFormat(linkPreview) {
        return {
            id: linkPreview.id,
            image_mimetype: linkPreview.image_mimetype,
            og_description: linkPreview.og_description,
            og_image: linkPreview.og_image,
            og_mimetype: linkPreview.og_mimetype,
            og_title: linkPreview.og_title,
            og_type: linkPreview.og_type,
            source_url: linkPreview.source_url
        };
    },
});
