/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { Dialog } from '@web/core/dialog/dialog';
import { SearchMedia } from './search_media';

const { Component, xml, useState, useRef, onWillStart } = owl;

export const IMAGE_MIMETYPES = ['image/jpg', 'image/jpeg', 'image/jpe', 'image/png', 'image/svg+xml', 'image/gif'];
export const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.jpe', '.png', '.svg', '.gif'];

class RemoveButton extends Component {
    setup() {
        this.removeTitle = this.env._t("This file is attached to the current record.");
        if (this.props.model === 'ir.ui.view') {
            this.removeTitle = this.env._t("This file is a public view attachment.");
        }
    }

    remove(ev) {
        ev.stopPropagation();
        this.props.remove();
    }
}
RemoveButton.template = xml`<i class="fa fa-trash o_existing_attachment_remove position-absolute top-0 end-0 p-2 bg-white-25 cursor-pointer opacity-0 opacity-100-hover z-index-1 transition-base" t-att-title="removeTitle" role="img" t-att-aria-label="removeTitle" t-on-click="this.remove"/>`;

export class AttachmentError extends Component {
    setup() {
        this.title = this.env._t("Alert");
    }
}
AttachmentError.components = { Dialog };
AttachmentError.template = xml `
<Dialog title="title">
    <div class="form-text">
        <p>The image could not be deleted because it is used in the
            following pages or views:</p>
        <ul t-foreach="props.views"  t-as="view" t-key="view.id">
            <li>
                <a t-att-href="'/web#model=ir.ui.view&amp;id=' + view.id">
                    <t t-esc="view.name"/>
                </a>
            </li>
        </ul>
    </div>
    <t t-set-slot="footer">
        <button class="btn btn-primary" t-on-click="() => this.props.close()">
            Ok
        </button>
    </t>
</Dialog>`;

export class Attachment extends Component {
    setup() {
        this.dialogs = useService('dialog');
        this.rpc = useService('rpc');
    }

    remove() {
        this.dialogs.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this file ?"),
            confirm: async () => {
                const prevented = await this.rpc('/web_editor/attachment/remove', {
                    ids: [this.props.id],
                });
                if (!Object.keys(prevented).length) {
                    this.props.onRemoved(this.props.id);
                } else {
                    this.dialogs.add(AttachmentError, {
                        views: prevented[this.props.id],
                    });
                }
            },
        });
    }
}
Attachment.components = {
    RemoveButton,
};

export class FileSelectorControlPanel extends Component {
    setup() {
        this.state = useState({
            showUrlInput: false,
            urlInput: '',
            isValidUrl: false,
            isValidFileFormat: false
        });

        this.fileInput = useRef('file-input');
    }

    get showSearchServiceSelect() {
        return this.props.searchService && this.props.needle;
    }

    get enableUrlUploadClick() {
        return !this.state.showUrlInput || (this.state.urlInput && this.state.isValidUrl && this.state.isValidFileFormat);
    }

    async onUrlUploadClick() {
        if (!this.state.showUrlInput) {
            this.state.showUrlInput = true;
        } else {
            await this.props.uploadUrl(this.state.urlInput);
            this.state.urlInput = '';
        }
    }

    onUrlInput(ev) {
        const { isValidUrl, isValidFileFormat } = this.props.validateUrl(ev.target.value);
        this.state.isValidFileFormat = isValidFileFormat;
        this.state.isValidUrl = isValidUrl;
    }

    onClickUpload() {
        this.fileInput.el.click();
    }

    async onChangeFileInput() {
        const inputFiles = this.fileInput.el.files;
        if (!inputFiles.length) {
            return;
        }
        await this.props.uploadFiles(inputFiles);
        this.fileInput.el.value = '';
    }
}
FileSelectorControlPanel.template = 'web_editor.FileSelectorControlPanel';
FileSelectorControlPanel.components = {
    SearchMedia,
};

export class FileSelector extends Component {
    setup() {
        this.orm = useService('orm');
        this.uploadService = useService('upload');

        this.state = useState({
            attachments: [],
            canLoadMoreAttachments: true,
            isFetchingAttachments: false,
            needle: '',
        });

        this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY = 10;

        onWillStart(async () => {
            this.state.attachments = await this.fetchAttachments(this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY, 0);
        });
    }

    get canLoadMore() {
        return this.state.canLoadMoreAttachments;
    }

    get hasContent() {
        return this.state.attachments.length;
    }

    get isFetching() {
        return this.state.isFetchingAttachments;
    }

    get selectedAttachmentIds() {
        return this.props.selectedMedia[this.props.id].filter(media => media.mediaType === 'attachment').map(({ id }) => id);
    }

    get attachmentsDomain() {
        const domain = [
            '&',
            ['res_model', '=', this.props.resModel],
            ['res_id', '=', this.props.resId || 0]
        ];
        domain.unshift('|', ['public', '=', true]);
        domain.push(['name', 'ilike', this.state.needle]);
        return domain;
    }

    validateUrl(url) {
        const path = url.split('?')[0];
        const isValidUrl = /^.+\..+$/.test(path); // TODO improve
        const isValidFileFormat = true;
        return { isValidUrl, isValidFileFormat, path };
    }

    async fetchAttachments(limit, offset) {
        this.state.isFetchingAttachments = true;
        let attachments = [];
        try {
            attachments = await this.orm.call(
                'ir.attachment',
                'search_read',
                [],
                {
                    domain: this.attachmentsDomain,
                    fields: ['name', 'mimetype', 'description', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height', 'original_id'],
                    order: 'id desc',
                    // Try to fetch first record of next page just to know whether there is a next page.
                    limit: limit + 1,
                    offset,
                }
            );
        } catch (e) {
            // Reading attachments as a portal user is not permitted and will raise
            // an access error so we catch the error silently and don't return any
            // attachment so he can still use the wizard and upload an attachment
            if (e.exceptionName !== 'odoo.exceptions.AccessError') {
                throw e;
            }
        }
        this.state.canLoadMoreAttachments = attachments.length >= this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;
        this.state.isFetchingAttachments = false;
        return attachments;
    }

    async loadMore() {
        const newAttachments = await this.fetchAttachments(this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY, this.state.attachments.length);
        this.state.attachments.push(...newAttachments);
    }

    async search(needle) {
        this.state.needle = needle;
        this.state.attachments = await this.fetchAttachments(this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY, 0);
    }

    async uploadFiles(files) {
        await this.uploadService.uploadFiles(files, { resModel: this.props.resModel, resId: this.props.resId }, attachment => this.onUploaded(attachment));
    }

    async uploadUrl(url) {
        await this.uploadService.uploadUrl(url, { resModel: this.props.resModel, resId: this.props.resId }, attachment => this.onUploaded(attachment));
    }

    async onUploaded(attachment) {
        this.state.attachments = [attachment, ...this.state.attachments];
        this.selectAttachment(attachment);
        if (!this.props.multiSelect) {
            await this.props.save();
        }
    }

    onRemoved(attachmentId) {
        this.state.attachments = this.state.attachments.filter(attachment => attachment.id !== attachmentId);
    }

    selectAttachment(attachment) {
        this.props.selectMedia({ ...attachment, mediaType: 'attachment' });
    }

    selectInitialMedia() {
        return this.props.media
            && this.constructor.tagNames.includes(this.props.media.tagName)
            && !this.selectedAttachmentIds.length;
    }
}
FileSelector.template = 'web_editor.FileSelector';
FileSelector.components = {
    FileSelectorControlPanel,
};
