/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowButtonView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {FollowButtonView}
     */
    get followButtonView() {
        return this.props.record;
    }

}

Object.assign(FollowButtonView, {
    props: { record: Object },
    template: 'mail.FollowButtonView',
});

registerMessagingComponent(FollowButtonView);
