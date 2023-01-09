/** @odoo-module */

import { Attachment, FileSelector, IMAGE_MIMETYPES } from './file_selector';

export class DocumentAttachment extends Attachment {}
DocumentAttachment.template = 'web_editor.DocumentAttachment';

export class DocumentSelector extends FileSelector {
    setup() {
        super.setup();

        this.uploadText = this.env._t("Upload a document");
        this.urlPlaceholder = "https://www.odoo.com/mydocument";
        this.addText = this.env._t("Add document");
        this.searchPlaceholder = this.env._t("Search a document");
        this.allLoadedText = this.env._t("All documents have been loaded");
    }

    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push(['mimetype', 'not in', IMAGE_MIMETYPES]);
        // The assets should not be part of the documents.
        // All assets begin with '/web/assets/', see _get_asset_template_url().
        domain.unshift('&', '|', ['url', '=', null], '!', ['url', '=like', '/web/assets/%']);
        return domain;
    }

    async onClickDocument(document) {
        this.selectAttachment(document);
        await this.props.save();
    }

    async fetchAttachments(...args) {
        const attachments = await super.fetchAttachments(...args);

        if (this.selectInitialMedia()) {
            for (const attachment of attachments) {
                if (`/web/content/${attachment.id}` === this.props.media.getAttribute('href').replace(/[?].*/, '')) {
                    this.selectAttachment(attachment);
                }
            }
        }
        return attachments;
    }

    /**
     * Utility method used by the MediaDialog component.
     */
    static async createElements(selectedMedia, { orm }) {
        return Promise.all(selectedMedia.map(async attachment => {
            const linkEl = document.createElement('a');
            let href = `/web/content/${attachment.id}?unique=${attachment.checksum}&download=true`;
            if (!attachment.public) {
                let accessToken = attachment.access_token;
                if (!accessToken) {
                    [accessToken] = await orm.call(
                        'ir.attachment',
                        'generate_access_token',
                        [attachment.id],
                    );
                }
                href += `&access_token=${accessToken}`;
            }
            linkEl.href = href;
            linkEl.title = attachment.name;
            linkEl.dataset.mimetype = attachment.mimetype;
            return linkEl;
        }));
    }
}
DocumentSelector.mediaSpecificClasses = ['o_image'];
DocumentSelector.mediaSpecificStyles = [];
DocumentSelector.mediaExtraClasses = [];
DocumentSelector.tagNames = ['A'];
DocumentSelector.attachmentsListTemplate = 'web_editor.DocumentsListTemplate';
DocumentSelector.components = {
    ...FileSelector.components,
    DocumentAttachment,
};
