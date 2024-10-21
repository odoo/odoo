import { LinkPreview } from "@mail/core/common/link_preview";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview[]} linkPreviews
 * @property {boolean} [deletable]
 * @extends {Component<Props, Env>}
 */
export class LinkPreviewList extends Component {
    static template = "mail.LinkPreviewList";
    static props = ["linkPreviews", "deletable?"];
    static defaultProps = {
        deletable: false,
    };
    static components = { LinkPreview };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }

    get linkPreviewList() {
        return this.props.linkPreviews.filter((linkPreview) => {
            if (linkPreview.isImage && this.store.settings.link_preview_image) {
                return true;
            }
            if (!linkPreview.isImage && this.store.settings.link_preview_html) {
                return true;
            }
            return false;
        });
    }
}
