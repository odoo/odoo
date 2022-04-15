/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { markEventHandled } from '@mail/utils/utils';
const { Component } = owl;

export class Follower extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Follower}
     */
    get follower() {
        return this.messaging && this.messaging.models['Follower'].get(this.props.followerLocalId);
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
        if (this.props.chatterLocalId) {
            const chatter = this.messaging.models['Chatter'].get(this.props.chatterLocalId);
            if (chatter) {
                chatter.reloadParentView({ fieldNames: ['message_follower_ids'] });
            }
        }
        if (this.props.onHideFollowerListMenu) {
            this.props.onHideFollowerListMenu();
        }
    }

}

Object.assign(Follower, {
    props: {
        chatterLocalId: {
            type: String,
            optional: true,
        },
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
