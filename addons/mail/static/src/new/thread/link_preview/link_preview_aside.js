/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { LinkPreviewConfirmDelete } from "./link_preview_confirm_delete";

export class LinkPreviewAside extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }

    onClick() {
        this.dialogService.add(LinkPreviewConfirmDelete, {
            linkPreview: this.props.linkPreview,
            LinkPreviewListComponent: this.env.LinkPreviewListComponent,
        });
    }
}

Object.assign(LinkPreviewAside, {
    template: "mail.link_preview_aside",
    props: ["linkPreview", "className?"],
});
