/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ChatterTopbar extends Component {

    /**
     * @returns {ChatterTopbar}
     */
    get chatterTopbar() {
        return this.props.record;
    }

}

Object.assign(ChatterTopbar, {
    props: { record: Object },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
