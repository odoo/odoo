import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @prop {(persona: import("models").Persona) => string} [avatarClass]
 * Function used to determine extra classes for the avatars.
 * @prop {Array} personas List of personas to display in the stack.
 * @prop {"v"|"h"} [direction] Determine the direction of the
 * stack (vertical or horizontal).
 * @prop {number} [max] Maximum number of personas to display in the stack. An
 * hidden count will be displayed if there are more personas than max.
 * @prop {number} [size] Size of the avatars, in pixel.
 * @extends {Component<Props, Env>}
 */
export class AvatarStack extends Component {
    static template = "mail.AvatarStack";
    static props = {
        direction: { type: String, optional: true, validate: (d) => ["v", "h"].includes(d) },
        avatarClass: { type: Function, optional: true },
        max: { type: Number, optional: true },
        personas: Array,
        size: { type: Number, optional: true },
        slots: { optional: true },
    };
    static defaultProps = {
        avatarClass: () => "",
        max: 4,
        size: 24,
        direction: "h",
    };

    getStyle(index) {
        let style = `width: ${this.props.size}px; height: ${this.props.size}px;`;
        if (index === 0) {
            return style;
        }
        // Compute cumulative offset,
        const marginDirection = this.props.direction === "v" ? "top" : "left";
        style += `margin-${marginDirection}: -${this.props.size / 3}px`;
        return style;
    }
}
