/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class Discuss extends LegacyComponent {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.props.record;
    }
}

Object.assign(Discuss, {
    props: { record: Object },
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
