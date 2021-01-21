odoo.define('mail/static/src/components/attachment_delete_confirm_dialog/attachment_delete_confirm_dialog.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    Dialog: require('web.OwlDialog'),
};

const { Component } = owl;
const { useRef } = owl.hooks;

class AttachmentDeleteConfirmDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const attachment = this.env.models['mail.attachment'].get(props.attachmentLocalId);
            return {
                attachment: attachment ? attachment.__state : undefined,
            };
        });
        // to manually trigger the dialog close event
        this._dialogRef = useRef('dialog');
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
     * @returns {string}
     */
    getBody() {
        return _.str.sprintf(
            this.env._t(`Do you really want to delete "%s"?`),
            owl.utils.escape(this.attachment.displayName)
        );
    }

    /**
     * @returns {string}
     */
    getTitle() {
        return this.env._t("Confirmation");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickCancel() {
        this._dialogRef.comp._close();
    }

    /**
     * @private
     */
    _onClickOk() {
        this._dialogRef.comp._close();
        this.attachment.remove();
        this.trigger('o-attachment-removed', { attachmentLocalId: this.props.attachmentLocalId });
    }

}

Object.assign(AttachmentDeleteConfirmDialog, {
    components,
    props: {
        attachmentLocalId: String,
    },
    template: 'mail.AttachmentDeleteConfirmDialog',
});

return AttachmentDeleteConfirmDialog;

});
