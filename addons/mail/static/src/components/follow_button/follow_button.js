/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowButton extends Component {

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

Object.assign(FollowButton, {
    props: { record: Object },
    template: 'mail.FollowButton',
});

registerMessagingComponent(FollowButton);
