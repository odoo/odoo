import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview} linkPreview
 * @property {function} [delete] Function bound to the delete button
 * @property {function} [deleteAll] Function bound to the delete all button
 * @property {function} close
 * @property {Component} LinkPreviewListComponent
 * @extends {Component<Props, Env>}
 */
export class LinkPreviewConfirmDelete extends Component {
    static components = { Dialog };
    static props = ["LinkPreview", "messageLinkPreview", "close"];
    static template = "mail.LinkPreviewConfirmDelete";

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    onClickOk() {
        this.props.messageLinkPreview.hide();
        this.props.close();
    }

    onClickDeleteAll() {
        this.props.messageLinkPreview.message_id.hideAllLinkPreviews();
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
