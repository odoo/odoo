odoo.define('mail.component.Attachment', function () {
'use strict';

class Attachment extends owl.store.ConnectedComponent {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get attachmentUrl() {
        if (this.storeProps.attachment.isTemporary) {
            return '';
        }
        return this.env.session.url('/web/content', {
            id: this.storeProps.attachment.id,
            download: true,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDownload(ev) {
        window.location = `/web/content/ir.attachment/${this.storeProps.attachment.id}/datas?download=true`;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (!this.env.store.getters.isAttachmentViewable(this.props.attachmentLocalId)) {
            return;
        }
        this.dispatch('viewAttachments', {
            attachmentLocalId: this.props.attachmentLocalId,
            attachmentLocalIds: this.props.attachmentLocalIds.filter(localId =>
                this.env.store.getters.isAttachmentViewable(localId)),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink(ev) {
        this.dispatch('unlinkAttachment', this.props.attachmentLocalId);
    }
}

Attachment.defaultProps = {
    hasLabelForCardLayout: true,
    imageSizeForBasicLayout: 'medium',
    isDownloadable: false,
    isEditable: true,
    layout: 'basic',
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.attachmentLocalId
 */
Attachment.mapStoreToProps = function (state, ownProps) {
    return {
        attachment: state.attachments[ownProps.attachmentLocalId],
    };
};

Attachment.props = {
    attachment: Object, // {mail.store.model.Attachment}
    attachmentLocalId: String,
    hasLabelForCardLayout: Boolean,
    imageSizeForBasicLayout: String, // ['small', 'medium', 'large']
    isDownloadable: Boolean,
    isEditable: Boolean,
    layout: String, // ['basic', 'card']
};

Attachment.template = 'mail.component.Attachment';

return Attachment;

});
