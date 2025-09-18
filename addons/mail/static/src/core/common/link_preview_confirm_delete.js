import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";
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

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    get message() {
        return this.props.linkPreview.message_id;
    }

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
