import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class AvatarStack extends Component {
    static template = "mail.AvatarStack";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props(
            {
                "avatarClass?": types.function(
                    [
                        types.or([
                            types.instanceOf(this.store["res.partner"].Class),
                            types.instanceOf(this.store["mail.guest"].Class),
                        ]),
                    ],
                    types.string()
                ),
                "containerClass?": types.string(),
                "direction?": types.selection(["h", "v"]),
                "max?": types.number(),
                "onClick?": types.function([types.instanceOf(MouseEvent)]),
                personas: types.array(
                    types.or([
                        types.instanceOf(this.store["res.partner"].Class),
                        types.instanceOf(this.store["mail.guest"].Class),
                    ])
                ),
                "size?": types.number(),
                "spacing?": types.number(),
                "total?": types.number(),
            },
            {
                avatarClass: () => "",
                direction: "h",
                max: 4,
                onClick: () => {},
                size: 24,
                spacing: 8,
            }
        );
    }

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
