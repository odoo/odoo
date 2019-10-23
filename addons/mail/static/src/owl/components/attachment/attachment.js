odoo.define('mail.component.Attachment', function () {
'use strict';

const { Component } = owl;
const { useDispatch, useGetters, useStore } = owl.hooks;

class Attachment extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            return {
                attachment: state.attachments[props.attachmentLocalId],
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return the url of the attachment. Temporary attachments, a.k.a. uploading
     * attachments, do not have an url.
     *
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

    /**
     * Get the details mode after auto mode is computed
     *
     * @return {string} 'card', 'hover' or 'none'
     */
    get detailsMode() {
        if (this.props.detailsMode !== 'auto') {
            return this.props.detailsMode;
        }
        const fileType =
            this.storeGetters.attachmentFileType(this.props.attachmentLocalId);
        if (fileType !== 'image') {
            return 'card';
        }
        return 'hover';
    }

    /**
     * Get the attachment representation style to be applied
     *
     * @return {string}
     */
    get imageStyle() {
        const fileType =
            this.storeGetters.attachmentFileType(this.props.attachmentLocalId);
        if (fileType !== 'image') {
            return '';
        }
        let size;
        if (this.detailsMode === 'card') {
            size = '38x38';
        } else {
            size = '160x160';
        }
        const attachmentId = this.storeProps.attachment.id;
        return `background-image:url(/web/image/${attachmentId}/${size}/?crop=true);`;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Download the attachment when clicking on donwload icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDownload(ev) {
        const attachmentId = this.storeProps.attachment.id;
        window.location = `/web/content/ir.attachment/${attachmentId}/datas?download=true`;
    }

    /**
     * Open the attachment viewer when clicking on viewable attachment.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (!this.storeGetters.isAttachmentViewable(this.props.attachmentLocalId)) {
            return;
        }
        this.storeDispatch('viewAttachments', {
            attachmentLocalId: this.props.attachmentLocalId,
            attachmentLocalIds: this.props.attachmentLocalIds,
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
    detailsMode: 'auto',
    isDownloadable: false,
    isEditable: true,
    showExtension: true,
    showFilename: true,
};

Attachment.props = {
    attachmentLocalId: {
        type: String,
    },
    attachmentLocalIds: {
        type: Array,
        element: String,
    },
    detailsMode: {
        type: String,
    }, //['auto', 'card', 'hover', 'none']
    isDownloadable: {
        type: Boolean,
    },
    isEditable: {
        type: Boolean,
    },
    showExtension: {
        type: Boolean,
    },
    showFilename: {
        type: Boolean,
    },
};

Attachment.template = 'mail.component.Attachment';

return Attachment;

});
