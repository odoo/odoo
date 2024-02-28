/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTypingIcon extends Component {}

Object.assign(ThreadTypingIcon, {
    defaultProps: {
        animation: 'none',
        size: 'small',
    },
    props: {
        animation: {
            type: String,
            validate: prop => ['bounce', 'none', 'pulse'].includes(prop),
            optional: true,
        },
        size: {
            type: String,
            validate: prop => ['small', 'medium'].includes(prop),
            optional: true,
        },
        title: {
            type: String,
            optional: true,
        }
    },
    template: 'mail.ThreadTypingIcon',
});

registerMessagingComponent(ThreadTypingIcon);
