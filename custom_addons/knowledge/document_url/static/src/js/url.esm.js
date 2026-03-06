/** @odoo-module **/

import {AttachmentList} from "@mail/core/common/attachment_list";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {url} from "@web/core/utils/urls";
import {_t} from "@web/core/l10n/translation";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },
    _onAddUrl(event) {
        event.preventDefault();
        event.stopPropagation();
        this.action.doAction("document_url.action_ir_attachment_add_url", {
            additionalContext: {
                active_id: this.state.thread.id,
                active_ids: [this.state.thread.id],
                active_model: this.state.thread.model,
            },
            onClose: async () => {
                await this.updateThreadAttachments();
            },
        });
    },
    async updateThreadAttachments() {
        const attachments = await this.orm.call("ir.attachment", "search_read", [
            [
                ["res_model", "=", this.state.thread.model],
                ["res_id", "=", this.state.thread.id],
            ],
            ["id", "name", "mimetype", "url"],
        ]);
        this.state.thread.attachments = attachments.map((att) => ({
            id: att.id,
            name: att.name,
            mimetype: att.mimetype,
            url: att.url,
        }));
    },
    onClickAddAttachments(ev) {
        ev.stopPropagation();
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.rootRef.el.scrollTop = 0;
            this.state.thread.scrollTop = 0;
        }
    },
});

patch(AttachmentList.prototype, {
    /**
     * Return the url of the attachment. Temporary attachments, a.k.a. uploading
     * attachments, do not have an url.
     *
     * @param {Object} attachment
     * @returns {String}
     */
    canDownload(attachment) {
        return (
            super.canDownload(attachment) && attachment.mimetype !== "application/link"
        );
    },
    get attachmentUrl() {
        return url("/web/content", {
            id: this.attachment.id,
            download: true,
        });
    },
    onClickUnlink(attachment) {
        if (this.env.inComposer) {
            return this.props.unlinkAttachment(attachment);
        }
        this.dialog.add(ConfirmationDialog, {
            body: _t('Do you really want to delete "%s"?', attachment.name),
            // eslint-disable-next-line no-empty-function
            cancel: () => {},
            confirm: () => this.onConfirmUnlink(attachment),
        });
    },
});
