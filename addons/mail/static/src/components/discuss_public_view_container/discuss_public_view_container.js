/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/components/discuss_public_view/discuss_public_view';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class DiscussPublicViewContainer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.env.services.messaging.get().then(messaging => {
            messaging.models['Thread'].insert(messaging.models['Thread'].convertData(this.props.data.channelData));
            this.discussPublicView = messaging.models['DiscussPublicView'].insert(this.props.data.discussPublicViewData);
            if (this.discussPublicView.shouldDisplayWelcomeViewInitially) {
                this.discussPublicView.switchToWelcomeView();
            } else {
                this.discussPublicView.switchToThreadView();
            }
            this.render();
        });
    }

}

Object.assign(DiscussPublicViewContainer, {
    components: { DiscussPublicView: getMessagingComponent('DiscussPublicView') },
    template: 'mail.DiscussPublicViewContainer',
    props: {
        data: Object,
    },
});
