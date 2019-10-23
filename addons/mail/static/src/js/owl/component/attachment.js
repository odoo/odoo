odoo.define('mail.component.Attachment', function () {
'use strict';

class Attachment extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
            return {
                attachment: state.attachments[props.attachmentLocalId],
            };
        });
    }

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
        if (!this.storeGetters.isAttachmentViewable(this.props.attachmentLocalId)) {
            return;
        }
        this.storeDispatch('viewAttachments', {
            attachmentLocalId: this.props.attachmentLocalId,
            attachmentLocalIds: this.props.attachmentLocalIds.filter(localId =>
                this.storeGetters.isAttachmentViewable(localId)),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink(ev) {
        this.storeDispatch('unlinkAttachment', this.props.attachmentLocalId);
    }
}

Attachment.defaultProps = {
    attachmentLocalIds: [],
    hasLabelForCardLayout: true,
    imageSizeForBasicLayout: 'medium',
    isDownloadable: false,
    isEditable: true,
    layout: 'basic',
};

Attachment.props = {
    attachmentLocalId: String,
    attachmentLocalIds: {
        type: Array,
        element: String,
        optional: true,
    },
    hasLabelForCardLayout: Boolean,
    imageSizeForBasicLayout: String, // ['small', 'medium', 'large']
    isDownloadable: Boolean,
    isEditable: Boolean,
    layout: String, // ['basic', 'card']
};

Attachment.template = 'mail.component.Attachment';

return Attachment;

});
