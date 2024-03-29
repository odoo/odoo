/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").LinkPreview} linkPreview
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
        this.store = useState(useService("mail.store"));
    }

    get message() {
        return this.props.linkPreview.message;
    }

    onClickOk() {
        this.rpc(
            "/mail/link_preview/delete",
            { link_preview_ids: [this.props.linkPreview.id] },
            { silent: true }
        );
        this.props.close();
    }

    onClickDeleteAll() {
        this.rpc(
            "/mail/link_preview/delete",
            { link_preview_ids: this.message.linkPreviews.map((lp) => lp.id) },
            { silent: true }
        );
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
