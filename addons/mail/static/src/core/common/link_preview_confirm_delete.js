import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";

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
    static props = ["linkPreview", "delete", "deleteAll?", "close", "LinkPreview"];
    static template = "mail.LinkPreviewConfirmDelete";

    onClickOk() {
        this.props.delete();
        this.props.close();
    }

    onClickDeleteAll() {
        this.props.deleteAll?.();
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
