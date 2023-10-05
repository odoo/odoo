/* @odoo-module */

import { LinkPreview } from "@mail/core/common/link_preview";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 */
export class LinkAttachment extends Component {
    static components = { LinkPreview };
    static props = ["links"];
    static template = "mail.LinkAttachment";
}
