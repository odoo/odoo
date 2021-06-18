/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class Attachment extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useComponentToModel({ fieldName: 'component', modelName: 'mail.attachment', propNameAsRecordLocalId: 'attachmentLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get attachment() {
        return this.messaging && this.messaging.models['mail.attachment'].get(this.props.attachmentLocalId);
    }

    /**
     * Return the url of the attachment. Uploading attachments do not have an url.
     *
     * @returns {string}
     */
    get attachmentUrl() {
        if (this.attachment.isUploading) {
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
        if (this.messaging.isQUnitTest) {
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
     * Open the attachment viewer when clicking on viewable attachment.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (!this.attachment.isViewable) {
            return;
        }
        this.messaging.models['mail.attachment'].view({
            attachment: this.attachment,
            attachments: this.props.attachmentLocalIds.map(
                attachmentLocalId => this.messaging.models['mail.attachment'].get(attachmentLocalId)
            ),
        });
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

registerMessagingComponent(Attachment, { propsCompareDepth: { attachmentLocalIds: 1 }});
