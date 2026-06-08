import { Component, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class AvatarStack extends Component {
    static template = "mail.AvatarStack";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            avatarClass: t
                .function(
                    [
                        t.or([
                            t.instanceOf(this.store["res.partner"].Class),
                            t.instanceOf(this.store["mail.guest"].Class),
                        ]),
                    ],
                    t.string()
                )
                .optional(() => () => ""),
            containerClass: t.string().optional(),
            direction: t.selection(["h", "v"]).optional("h"),
            max: t.number().optional(4),
            onClick: t.function([t.instanceOf(MouseEvent)]).optional(() => () => {}),
            personas: t.array(
                t.or([
                    t.instanceOf(this.store["res.partner"].Class),
                    t.instanceOf(this.store["mail.guest"].Class),
                ])
            ),
            size: t.number().optional(24),
            spacing: t.number().optional(8),
            total: t.number().optional(),
        });
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
