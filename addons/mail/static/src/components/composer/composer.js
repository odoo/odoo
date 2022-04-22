/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Composer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ComposerView' });
        useRefToModel({ fieldName: 'buttonEmojisRef', modelName: 'ComposerView', refName: 'buttonEmojis' });
        this._onDropZoneFilesDropped = this._onDropZoneFilesDropped.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when some files have been dropped in the dropzone.
     *
     * @private
     * @param {Object} detail
     * @param {FileList} detail.files
     */
    async _onDropZoneFilesDropped(detail) {
        await this.composerView.fileUploader.uploadFiles(detail.files);
        this.composerView.useDragVisibleDropZone.update({ isVisible: false });
    }

}

Object.assign(Composer, {
    props: { localId: String },
    template: 'mail.Composer',
});

registerMessagingComponent(Composer);
