odoo.define('mail/static/src/components/attachment_list/attachment_list.js', function (require) {
'use strict';

const components = {
    Attachment: require('mail/static/src/components/attachment/attachment.js'),
};

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class AttachmentList extends Component {

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
            const attachments = this.env.models['mail.attachment'].all().filter(attachment =>
                props.attachmentLocalIds.includes(attachment.localId)
            );
            return {
                attachments: attachments
                    ? attachments.map(attachment => attachment.__state)
                    : undefined,
            };
        }, {
            compareDepth: {
                attachments: 1,
            },
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment[]}
     */
    get attachments() {
        return this.env.models['mail.attachment'].all().filter(attachment =>
            this.props.attachmentLocalIds.includes(attachment.localId)
        );
    }

    /**
     * @returns {mail.attachment[]}
     */
    get imageAttachments() {
        return this.attachments.filter(attachment => attachment.fileType === 'image');
    }

    /**
     * @returns {mail.attachment[]}
     */
    get nonImageAttachments() {
        return this.attachments.filter(attachment => attachment.fileType !== 'image');
    }

    /**
     * @returns {mail.attachment[]}
     */
    get viewableAttachments() {
        return this.attachments.filter(attachment => attachment.isViewable);
    }

}

Object.assign(AttachmentList, {
    components,
    defaultProps: {
        attachmentLocalIds: [],
    },
    props: {
        areAttachmentsDownloadable: {
            type: Boolean,
            optional: true,
        },
        areAttachmentsEditable: {
            type: Boolean,
            optional: true,
        },
        attachmentLocalIds: {
            type: Array,
            element: String,
        },
        attachmentsDetailsMode: {
            type: String,
            optional: true,
            validate: prop => ['auto', 'card', 'hover', 'none'].includes(prop),
        },
        attachmentsImageSize: {
            type: String,
            optional: true,
            validate: prop => ['small', 'medium', 'large'].includes(prop),
        },
        showAttachmentsExtensions: {
            type: Boolean,
            optional: true,
        },
        showAttachmentsFilenames: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.AttachmentList',
});

return AttachmentList;

});
