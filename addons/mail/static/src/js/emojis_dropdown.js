/** @odoo-module **/

import emojis from '@mail/js/emojis';

const { Component } = owl;

export class EmojisDropdown extends Component {
    setup() {
        this.emojis = emojis;
        super.setup();
    }
};
EmojisDropdown.template = 'mail.EmojisDropdown';
