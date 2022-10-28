/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
