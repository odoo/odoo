import { useHover } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {Function} [onHover]
 * @property {Object[]} [slots]
 * @extends {Component<Props, Env>}
 */
export class HoverAnimation extends Component {
    static template = "mail.HoverAnimation";
    static props = {
        slots: { type: Object, optional: true },
        onHover: { type: Function, optional: true },
        animation: { type: String, validate: (a) => ["pop", "wobble", "rotate"].includes(a) },
        intensity: { type: Number, validate: (i) => i > 0 && i <= 5, optional: true },
    };
    static defaultProps = { intensity: 1 };

    setup() {
        this.state = useHover("root", { onHover: this.props.onHover });
    }
}

export class HoverAnimationTarget extends Component {
    static template = "mail.HoverAnimationTarget";
    static props = { slots: { type: Object, optional: true } };
}
