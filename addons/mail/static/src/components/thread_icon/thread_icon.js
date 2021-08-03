/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { ThreadTypingIcon } from '@mail/components/thread_typing_icon/thread_typing_icon';

const { Component } = owl;

const components = { ThreadTypingIcon };

export class ThreadIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadIcon, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadIcon',
});
