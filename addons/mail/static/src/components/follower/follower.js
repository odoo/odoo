/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { markEventHandled } from '@mail/utils/utils';
const { Component } = owl;

export class Follower extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.follower}
     */
    get follower() {
        return this.messaging && this.messaging.models['mail.follower'].get(this.props.followerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDetails(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.follower.openProfile();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEdit(ev) {
        ev.preventDefault();
        this.follower.showSubtypes();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickRemove(ev) {
        markEventHandled(ev, 'Follower.clickRemove');
        await this.follower.remove();
        this.trigger('reload', { fieldNames:['message_follower_ids'], keepChanges: true });
        if (this.props.onHideFollowerListMenu) {
            this.props.onHideFollowerListMenu();
        }
    }

}

Object.assign(Follower, {
    props: {
        followerLocalId: String,
        onClick: {
            type: Function,
            optional: true,
        },
        onHideFollowerListMenu: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.Follower',
});

registerMessagingComponent(Follower);
