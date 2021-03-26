/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';

const { Component } = owl;

class ThreadTypingIcon extends Component {

    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
    }

}

Object.assign(ThreadTypingIcon, {
    defaultProps: {
        animation: 'none',
        size: 'small',
    },
    props: {
        animation: {
            type: String,
            validate: prop => ['bounce', 'none', 'pulse'].includes(prop),
        },
        size: {
            type: String,
            validate: prop => ['small', 'medium'].includes(prop),
        },
        title: {
            type: String,
            optional: true,
        }
    },
    template: 'mail.ThreadTypingIcon',
});

export default ThreadTypingIcon;
