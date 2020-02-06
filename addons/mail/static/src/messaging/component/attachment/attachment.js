odoo.define('mail.messaging.component.Attachment', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class Attachment extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                attachment: this.env.entities.Attachment.get(props.attachmentLocalId),
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Attachment}
     */
    get attachment() {
        return this.env.entities.Attachment.get(this.props.attachmentLocalId);
    }

    /**
     * Return the url of the attachment. Temporary attachments, a.k.a. uploading
     * attachments, do not have an url.
     *
     * @returns {string}
     */
    get attachmentUrl() {
        if (this.attachment.isTemporary) {
            return '';
        }
        return this.env.session.url('/web/content', {
            id: this.attachment.id,
            download: true,
        });
    }

    /**
     * Get the details mode after auto mode is computed
     *
     * @returns {string} 'card', 'hover' or 'none'
     */
    get detailsMode() {
        if (this.props.detailsMode !== 'auto') {
            return this.props.detailsMode;
        }
        if (this.attachment.fileType !== 'image') {
            return 'card';
        }
        return 'hover';
    }

    /**
     * Get the attachment representation style to be applied
     *
     * @returns {string}
     */
    get imageStyle() {
        if (this.attachment.fileType !== 'image') {
            return '';
        }
        let size;
        if (this.detailsMode === 'card') {
            size = '38x38';
        } else {
            size = '160x160';
        }
        return `background-image:url(/web/image/${this.attachment.id}/${size}/?crop=true);`;
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
        ev.stopPropagation();
        window.location = `/web/content/ir.attachment/${this.attachment.id}/datas?download=true`;
    }

    /**
     * Open the attachment viewer when clicking on viewable attachment.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (!this.attachment.isViewable) {
            return;
        }
        this.env.entities.Attachment.view({
            attachment: this.attachment,
            attachments: this.props.attachmentLocalIds.map(
                attachmentLocalId => this.env.entities.Attachment.get(attachmentLocalId)
            ),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink(ev) {
        ev.stopPropagation();
        this.attachment.remove();
    }

}

Object.assign(Attachment, {
    defaultProps: {
        attachmentLocalIds: [],
        detailsMode: 'auto',
        imageSize: 'medium',
        isDownloadable: false,
        isEditable: true,
        showExtension: true,
        showFilename: true,
    },
    props: {
        attachmentLocalId: String,
        attachmentLocalIds: {
            type: Array,
            element: String,
        },
        detailsMode: String, //['auto', 'card', 'hover', 'none']
        imageSize: String, //['small', 'medium', 'large']
        isDownloadable: Boolean,
        isEditable: Boolean,
        showExtension: Boolean,
        showFilename: Boolean,
    },
    template: 'mail.messaging.component.Attachment',
});

return Attachment;

});
