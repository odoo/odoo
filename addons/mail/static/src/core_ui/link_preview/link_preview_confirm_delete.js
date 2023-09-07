/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useStore } from "@mail/core/messaging_hook";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/link_preview_model").LinkPreview} linkPreview
 * @property {function} close
 * @property {Component} LinkPreviewListComponent
 * @extends {Component<Props, Env>}
 */
export class LinkPreviewConfirmDelete extends Component {
    static components = { Dialog };
    static props = ["linkPreview", "close", "LinkPreview"];
    static template = "mail.LinkPreviewConfirmDelete";

    setup() {
        this.rpc = useService("rpc");
        this.store = useStore();
    }

    get message() {
        return this.store.messages[this.props.linkPreview.message.id];
    }

    onClickOk() {
        this.rpc(
            "/mail/link_preview/delete",
            { link_preview_id: this.props.linkPreview.id },
            { silent: true }
        );
        this.props.close();
    }

    onClickDeleteAll() {
        for (const linkPreview of this.message.linkPreviews) {
            this.rpc(
                "/mail/link_preview/delete",
                { link_preview_id: linkPreview.id },
                { silent: true }
            );
        }
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
