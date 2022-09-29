/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted } = owl;

export class AttachmentViewer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'imageRef', refName: 'image' });
        useRefToModel({ fieldName: 'zoomerRef', refName: 'zoomer' });
        useRefToModel({ fieldName: 'iframeViewerPdfRef', refName: 'iframeViewerPdf' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        onMounted(() => this._mounted());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        this.root.el.focus();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentViewer}
     */
    get attachmentViewer() {
        return this.props.record;
    }

}

Object.assign(AttachmentViewer, {
    props: { record: Object },
    template: 'mail.AttachmentViewer',
});

registerMessagingComponent(AttachmentViewer);
