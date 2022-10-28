/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
    props: { record: Object },
    template: 'mail.DropZone',
});

registerMessagingComponent(DropZone);
