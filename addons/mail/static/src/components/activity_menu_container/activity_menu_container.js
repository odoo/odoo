/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/components/activity_menu_view/activity_menu_view';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class ActivityMenuContainer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
            this.activityMenuView = this.env.services.messaging.modelManager.messaging.models['ActivityMenuView'].insert();
            this.render();
        });
    }

}

Object.assign(ActivityMenuContainer, {
    components: { ActivityMenuView: getMessagingComponent('ActivityMenuView') },
    template: 'mail.ActivityMenuContainer',
});
