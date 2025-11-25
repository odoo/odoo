import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @prop {(persona: import("models").Persona) => string} [avatarClass] Function
 * used to determine extra classes for the avatars.
 * @prop {Array} personas List of personas to display in the stack.
 * @prop {"v"|"h"} [direction] Determine the direction of the stack (vertical or
 * horizontal).
 * @prop {number} [max] Maximum number of personas to display in the stack. An
 * hidden count will be displayed if there are more personas than max.
 * @prop {number} [size] Size of the avatars, in pixel.
 * @prop {number} [total] Total number of avatars. Useful to avoid fetching
 * every persona while keeping an accurate counter.
 * @prop {number} [spacing] Spacing between the avatars in pixels. Will impact
 * negative margin which is used to position the avatars (the higher, the
 * closer).
 * @extends {Component<Props, Env>}
 */
export class AvatarStack extends Component {
    static template = "mail.AvatarStack";
    static props = {
        avatarClass: { type: Function, optional: true },
        containerClass: { type: String, optional: true },
        direction: { type: String, optional: true, validate: (d) => ["v", "h"].includes(d) },
        max: { type: Number, optional: true },
        onClick: { type: Function, optional: true },
        personas: Array,
        size: { type: Number, optional: true },
        slots: { optional: true },
        spacing: { type: Number, optional: true },
        total: { type: Number, optional: true },
    };
    static defaultProps = {
        avatarClass: () => "",
        onClick: () => {},
        max: 4,
        size: 24,
        direction: "h",
        spacing: 8,
    };

    getStyle(index) {
        const styles = [
            "box-sizing: content-box",
            `height: ${this.props.size}px`,
            `padding: 1.5px`,
            `width: ${this.props.size}px`,
            `z-index: ${this.props.personas.length + index}`,
        ];
        if (index !== 0) {
            // Compute cumulative offset,
            const marginDirection = this.props.direction === "v" ? "top" : "left";
            styles.push(`margin-${marginDirection}: -${this.props.spacing}px`);
        }
        return styles.join(";");
    }

    get remainingCount() {
        const total = this.props.total ?? this.props.personas.length;
        return total - Math.min(this.props.personas.length, this.props.max);
    }
}
