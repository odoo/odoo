/** @odoo-module **/

import { useMessagingContainer } from '@mail/component_hooks/use_messaging_container';

import { Component } from '@odoo/owl';

export class ActivityMenuContainer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useMessagingContainer();
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
            this.activityMenuView = this.env.services.messaging.modelManager.messaging.models['ActivityMenuView'].insert();
            this.render();
        });
    }

}
ActivityMenuContainer.props = {};

Object.assign(ActivityMenuContainer, {
    template: 'mail.ActivityMenuContainer',
});
