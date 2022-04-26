/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/discuss_public_view/discuss_public_view';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class DiscussPublicViewContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
    }

    get discussPublicView() {
        return this.messaging.models['DiscussPublicView'].findFromIdentifyingData(this.messaging);
    }

}

Object.assign(DiscussPublicViewContainer, {
    components: { DiscussPublicView: getMessagingComponent('DiscussPublicView') },
    template: 'mail.DiscussPublicViewContainer',
});
