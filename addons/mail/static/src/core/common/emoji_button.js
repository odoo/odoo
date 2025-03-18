import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HoverAnimation } from "./hover_animation";

/**
 * @typedef {Object} Props
 * @property {Function} onClick
 * @extends {Component<Props, Env>}
 */
export class EmojiButton extends Component {
    static template = "mail.EmojiButton";
    static props = { onClick: Function };
    static components = { HoverAnimation };

    setup() {
        super.setup(...arguments);
        this.ui = useState(useService("ui"));
        this.state = useState({ customIcon: null });
        this.smileys = ["😏", "😛", "😎", "😊", "😄", "😃", "😆", "🤣"];
    }

    onHover() {
        const smileysExceptCurrent = this.smileys.filter(
            (smiley) => smiley !== this.state.customIcon
        );
        this.state.customIcon =
            smileysExceptCurrent[Math.floor(Math.random() * smileysExceptCurrent.length)];
    }
}
