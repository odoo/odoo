/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AutoResizeImage, ImageSelector } from '@web_editor/components/media_dialog/image_selector';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { Dialog } from '@web/core/dialog/dialog';
import { UnsplashError } from '@web_unsplash/components/media_dialog/image_selector';
import { useService, useChildRef } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class AutoResizeCover extends AutoResizeImage {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    /**
     * @override
     * Open Dialog to delete the cover record.
     */
    remove() {
        this.dialogs.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this cover? It will be removed from every article it is used in."),
            confirm: async () => {
                const res = await this.orm.unlink(this.props.model,
                    [this.props.resId],
                );
                if (res) {
                    this.props.onRemoved(this.props.id, this.props.resId);
                }
            },
        });
    }
}

export class KnowledgeCoverSelector extends ImageSelector {
    setup() {
        super.setup();
        // Search for images matching the article name when opening the dialog.
        this.state.needle = this.props.searchTerm;
        this.searchUnsplash(this.state.needle);
    }

    /**
     * @override
     * Domain used to fetch the attachments to display in the coverSelector.
     */
    get attachmentsDomain() {
        return ['&', ['res_model', '=', this.props.resModel], ['name', 'ilike', this.state.needle]];
    }

    /**
     * @override
     * Update the article's cover using the id of the cover associated to the
     * attachment clicked.
     */
    onClickAttachment(attachment) {
        this.props.save(attachment.res_id);
    }

    /**
     * @override
     * Upload the unsplash image clicked.
     */
    onClickRecord(unsplashRecord) {
        this.uploadService.uploadUnsplashRecords(
            [unsplashRecord],
            {resModel: this.props.resModel, resId: this.props.resId},
            async (attachments) => this.onUploaded(attachments[0])
        );
    }

    /**
     * @override
     * Remove cover from the opened CoverSelector, and update article's cover
     * if the cover was used in the current article.
     */
    onRemoved(attachmentId, coverId) {
        super.onRemoved(attachmentId);
        if (coverId === this.props.articleCoverId) {
            this.props.save(false);
        }
    }

    /**
     * @override
     * Associate the created attachment to a new cover record, update the
     * attachment's resId, and update the article's cover.
     */
    async onUploaded(attachment) {
        const [coverId] = await this.orm.create(this.props.resModel, [{attachment_id: attachment.id}]);
        this.props.save(coverId);
    }

    /**
     * @override
     * Overriden to not throw an error.
     * Designed to be used with several tabs in the dialog (not the case here)
     * and used for rendering purposes to show selected images when multiImage
     * is allowed (not the case either).
     */
    get selectedAttachmentIds() {
        return [];
    }

    /**
     * @override
     * Overriden to not throw an error.
     * Designed to be used with several tabs in the dialog (not the case here)
     * and used for rendering purposes to show selected images when multiImage
     * is allowed (not the case either).
     */
    get selectedRecordIds() {
        return [];
    }
}

KnowledgeCoverSelector.defaultProps = {
    resModel: 'knowledge.cover',
    orientation: 'landscape',
};
KnowledgeCoverSelector.attachmentsListTemplate = 'knowledge.CoversListTemplate';
KnowledgeCoverSelector.components = {
    ...ImageSelector.components,
    AutoResizeCover,
    UnsplashError,
};

export class KnowledgeCoverDialog extends Component {
    setup() {
        this.size = 'xl';
        this.contentClass = 'o_select_media_dialog h-100';
        this.title = _t("Choose a nice cover");
        this.modalRef = useChildRef();
    }

    /**
     * Update the article's cover.
     */
    save(coverId) {
        this.props.save(coverId);
        this.props.close();
    }
}
KnowledgeCoverDialog.template = 'knowledge.KnowledgeCoverDialog';
KnowledgeCoverDialog.components = {
    KnowledgeCoverSelector,
    Dialog
};
