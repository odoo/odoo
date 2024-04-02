import { rpcWithEnv } from "@mail/utils/common/misc";
import { Component, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
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
        super.setup();
        this.store = useState(useService("mail.store"));
        rpc = rpcWithEnv(this.env);
    }

    get message() {
        return this.props.linkPreview.message;
    }

    onClickOk() {
        rpc(
            "/mail/link_preview/hide",
            { link_preview_ids: [this.props.linkPreview.id] },
            { silent: true }
        );
        this.props.close();
    }

    onClickDeleteAll() {
        rpc(
            "/mail/link_preview/hide",
            { link_preview_ids: this.message.linkPreviews.map((lp) => lp.id) },
            { silent: true }
        );
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
