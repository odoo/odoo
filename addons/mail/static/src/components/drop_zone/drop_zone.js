/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DropZone extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DropZoneView}
     */
    get dropZoneView() {
        return this.props.record;
    }

}

Object.assign(DropZone, {
    props: {
        record: Object,
        onDropzoneFilesDropped: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.DropZone',
});

registerMessagingComponent(DropZone);
