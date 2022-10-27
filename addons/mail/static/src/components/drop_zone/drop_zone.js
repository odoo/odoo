/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DropZoneView extends Component {

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

Object.assign(DropZoneView, {
    props: { record: Object },
    template: 'mail.DropZoneView',
});

registerMessagingComponent(DropZoneView);
