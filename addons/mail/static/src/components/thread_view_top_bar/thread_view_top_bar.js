/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import PartnerListing from '@mail/components/partner_listing/partner_listing';
import PartnerSelector from '@mail/components/partner_selector/partner_selector';

const components = { PartnerListing, PartnerSelector };
const { useState } = owl.hooks;

const { Component } = owl;

class ThreadViewTopbar extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.state = useState({ custom_name: this.props.custom_channel_name });
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get members() {
        return this.thread.members;
    }

    get members_count() {
        return this.thread.members.length;
    }

    get thread_name() {
        return this.thread.name;
    }

    /**
     * @returns {mail.thread_view}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickInviteButton() {
        this.env.messaging.selectablePartnersList.update({
            inputSearch: "",
            isOpened: true,
        });
    }
}

Object.assign(ThreadViewTopbar, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadViewTopbar',
});

export default ThreadViewTopbar;
