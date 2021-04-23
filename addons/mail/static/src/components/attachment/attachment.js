odoo.define('mail/static/src/components/attachment/attachment.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    AttachmentDeleteConfirmDialog: require('mail/static/src/components/attachment_delete_confirm_dialog/attachment_delete_confirm_dialog.js'),
};

const { Component, useState } = owl;

class Attachment extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps({
            compareDepth: {
                attachmentLocalIds: 1,
            },
        });
        useStore(props => {
            const attachment = this.env.models['mail.attachment'].get(props.attachmentLocalId);
            return {
                attachment: attachment ? attachment.__state : undefined,
            };
        });
        this.state = useState({
            hasDeleteConfirmDialog: false,
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get attachment() {
        return this.env.models['mail.attachment'].get(this.props.attachmentLocalId);
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
        if (this.env.isQUnitTest) {
            // background-image:url is hardly mockable, and attachments in
            // QUnit tests do not actually exist in DB, so style should not
            // be fetched at all.
            return '';
        }
        let size;
        if (this.detailsMode === 'card') {
            size = '38x38';
        } else {
            // The size of background-image depends on the props.imageSize
            // to sync with width and height of `.o_Attachment_image`.
            if (this.props.imageSize === "large") {
                size = '400x400';
            } else if (this.props.imageSize === "medium") {
                size = '200x200';
            } else if (this.props.imageSize === "small") {
                size = '100x100';
            }
        }
        // background-size set to override value from `o_image` which makes small image stretched
        return `background-image:url(/web/image/${this.attachment.id}/${size}); background-size: auto;`;
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
        this.env.models['mail.attachment'].view({
            attachment: this.attachment,
            attachments: this.props.attachmentLocalIds.map(
                attachmentLocalId => this.env.models['mail.attachment'].get(attachmentLocalId)
            ),
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink(ev) {
        ev.stopPropagation();
        if (!this.attachment) {
            return;
        }
        if (this.attachment.isLinkedToComposer) {
            this.attachment.remove();
            this.trigger('o-attachment-removed', { attachmentLocalId: this.props.attachmentLocalId });
        } else {
            this.state.hasDeleteConfirmDialog = true;
        }
    }

   /**
    * @private
    */
    _onDeleteConfirmDialogClosed() {
        this.state.hasDeleteConfirmDialog = false;
    }
}

Object.assign(Attachment, {
    components,
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
        detailsMode: {
            type: String,
            validate: prop => ['auto', 'card', 'hover', 'none'].includes(prop),
        },
        imageSize: {
            type: String,
            validate: prop => ['small', 'medium', 'large'].includes(prop),
        },
        isDownloadable: Boolean,
        isEditable: Boolean,
        showExtension: Boolean,
        showFilename: Boolean,
    },
    template: 'mail.Attachment',
});

return Attachment;

});
