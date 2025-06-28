/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { TextField } from '@web/views/fields/text/text_field';
import { PortalAttachDocument } from '../portal_attach_document/portal_attach_document';
import { ChatterAttachmentsViewer } from './chatter_attachments_viewer';
import { Component, useState, onWillUpdateProps, useRef } from "@odoo/owl";

export class ChatterComposer extends Component {
    setup() {
        this.rpc = useService('rpc');
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
            message: this.state.message,
            attachment_ids,
            attachment_tokens,
            res_model: this.props.resModel,
            res_id: this.props.resId,
            project_sharing_id: this.props.projectSharingId,
        };
    }

    async sendMessage() {
        this.clearErrors();
        if (!this.state.message && !this.state.attachments.length) {
            this.state.displayError = true;
            return;
        }

        await this.rpc(
            "/mail/chatter_post",
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
        for (const file of files) {
            file.state = 'pending';
            this.state.attachments.push(file);
        }
    }

    async deleteAttachment(attachment) {
        this.clearErrors();
        try {
            await this.rpc(
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

ChatterComposer.components = {
    ChatterAttachmentsViewer,
    PortalAttachDocument,
    TextField,
};

ChatterComposer.props = {
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
ChatterComposer.defaultProps = {
    allowComposer: true,
    displayComposer: false,
    isUserPublic: true,
    token: '',
    attachments: [],
};

ChatterComposer.template = 'project.ChatterComposer';
