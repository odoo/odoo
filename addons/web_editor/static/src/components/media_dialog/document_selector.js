/** @odoo-module */

import utils from 'web.utils';
import { Attachment, FileSelector, IMAGE_MIMETYPES } from './file_selector';

const { useEffect } = owl;

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

        useEffect(() => {
            const initWithMedia = async () => {
                if (this.props.media && this.props.media.tagName === 'A') {
                    const selectedMedia = this.state.attachments.filter(attachment => `/web/content/${attachment.id}` === this.props.media.getAttribute('href').replace(/[?].*/, ''))[0];
                    if (selectedMedia) {
                        await this.selectAttachment(selectedMedia, false);
                    }
                }
            };

            initWithMedia();
        }, () => []);
    }

    get attachmentsDomain() {
        let domain = super.attachmentsDomain;
        domain = domain.concat([['mimetype', 'not in', IMAGE_MIMETYPES]]);
        domain = domain.concat('!', utils.assetsDomain());
        return domain;
    }
}
DocumentSelector.attachmentsListTemplate = 'web_editor.DocumentsListTemplate';
DocumentSelector.components = {
    ...FileSelector.components,
    DocumentAttachment,
};
