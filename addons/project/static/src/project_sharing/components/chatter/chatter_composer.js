/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { TextField } from '@web/views/fields/text/text_field';
import { PortalAttachDocument } from '../portal_attach_document/portal_attach_document';
import { ChatterAttachmentsViewer } from './chatter_attachments_viewer';
import { Component, useState, onWillUpdateProps, useRef } from "@odoo/owl";

export class ChatterComposer extends Component {
    static template = "project.ChatterComposer";
    static components = {
        ChatterAttachmentsViewer,
        PortalAttachDocument,
        TextField,
    };
    static props = {
        resModel: String,
        projectSharingId: Number,
        resId: { type: Number, optional: true },
        allowComposer: { type: Boolean, optional: true },
        displayComposer: { type: Boolean, optional: true },
        token: { type: String, optional: true },
        messageCount: { type: Number, optional: true },
        isUserPublic: { type: Boolean, optional: true },
        partnerId: { type: Number, optional: true },
        postProcessMessageSent: { type: Function, optional: true },
        attachments: { type: Array, optional: true },
    };
    static defaultProps = {
        allowComposer: true,
        displayComposer: false,
        isUserPublic: true,
        token: "",
        attachments: [],
    };

    setup() {
        this.state = useState({
            displayError: false,
            attachments: this.props.attachments.map(file => file.state === 'done'),
            message: '',
            loading: false,
        });
        this.inputRef = useRef("textarea");

        onWillUpdateProps(this.onWillUpdateProps);
    }

    onWillUpdateProps(nextProps) {
        this.clearErrors();
        this.state.message = '';
        if (this.inputRef.el) {
            this.inputRef.el.value = "";
        }
        this.state.attachments = nextProps.attachments.map(file => file.state === 'done');
    }

    get discussionUrl() {
        return `${window.location.href.split('#')[0]}#discussion`;
    }

    update() {
        this.clearErrors();
        this.state.message = this.inputRef.el.value;
    }

    prepareMessageData() {
        const attachment_ids = [];
        const attachment_tokens = [];
        for (const attachment of this.state.attachments) {
            attachment_ids.push(attachment.id);
            attachment_tokens.push(attachment.access_token);
        }
        return {
            thread_model: this.props.resModel,
            thread_id: this.props.resId,
            post_data: {
                body: this.state.message,
                attachment_ids,
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            attachment_tokens,
            project_sharing_id: this.props.projectSharingId,
        };
    }

    async sendMessage() {
        this.clearErrors();
        if (!this.state.message && !this.state.attachments.length) {
            this.state.displayError = true;
            return;
        }

        await rpc(
            "/mail/message/post",
            this.prepareMessageData(),
        );
        this.props.postProcessMessageSent();
        this.state.message = "";
        this.state.attachments = [];
    }

    clearErrors() {
        this.state.displayError = false;
    }

    async beforeUploadFile() {
        this.state.loading = true;
        return true;
    }

    onFileUpload(files) {
        this.state.loading = false;
        this.clearErrors();
        for (const fileData of files) {
            let file = fileData.data["ir.attachment"][0];
            file.state = 'pending';
            this.state.attachments.push(file);
        }
    }

    async deleteAttachment(attachment) {
        this.clearErrors();
        try {
            await rpc(
                '/portal/attachment/remove',
                {
                    attachment_id: attachment.id,
                    access_token: attachment.access_token,
                },
            );
        } catch (err) {
            console.error(err);
            this.state.displayError = true;
        }
        this.state.attachments = this.state.attachments.filter(a => a.id !== attachment.id);
    }
}
