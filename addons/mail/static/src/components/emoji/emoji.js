/** @odoo-module */

const { Component } = owl;
import { useEmojis } from "./emoji_hook"

export class Emoji extends Component {
    
    setup() {
        super.setup(...arguments);
        this.unicode = this.props.unicode;
        useEmojis();
    }

}

Object.assign(Emoji, {
    props: {
        unicode: String
    },
    template: 'mail.Emoji',
});