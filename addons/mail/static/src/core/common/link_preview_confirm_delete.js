/* @odoo-module */

<<<<<<< HEAD
import { Component, useState } from "@odoo/owl";
||||||| parent of bec1c11ce90 (temp)
import { Component } from "@odoo/owl";
=======
import { useStore } from "@mail/core/common/messaging_hook";

import { Component } from "@odoo/owl";
>>>>>>> bec1c11ce90 (temp)

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/link_preview_model").LinkPreview} linkPreview
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
<<<<<<< HEAD
        this.store = useState(useService("mail.store"));
    }

    get message() {
        return this.store.Message.get(this.props.linkPreview.message_id);
||||||| parent of bec1c11ce90 (temp)
=======
        this.store = useStore();
    }

    get message() {
        return this.store.messages[this.props.linkPreview.message.id];
>>>>>>> bec1c11ce90 (temp)
    }

    onClickOk() {
        this.rpc(
            "/mail/link_preview/delete",
<<<<<<< HEAD
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
||||||| parent of bec1c11ce90 (temp)
            { link_preview_id: this.props.linkPreview.id },
            { shadow: true }
=======
            { link_preview_id: this.props.linkPreview.id },
            { silent: true }
>>>>>>> bec1c11ce90 (temp)
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
