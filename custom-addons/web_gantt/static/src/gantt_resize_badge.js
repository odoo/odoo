/** @odoo-module **/

import { Component } from "@odoo/owl";

export class GanttResizeBadge extends Component {
    static props = {
        reactive: {
            type: Object,
            shape: {
                position: {
                    type: Object,
                    shape: {
                        top: Number,
                        right: { type: Number, optional: true },
                        left: { type: Number, optional: true },
                    },
                    optional: true,
                },
                diff: { type: Number, optional: true },
                scale: { type: String, optional: true },
            },
        },
    };
    static template = "web_gantt.GanttResizeBadge";

    get diff() {
        return this.props.reactive.diff || 0;
    }

    get diffText() {
        const { diff, props } = this;
        const prefix = this.diff > 0 ? "+" : "";
        return `${prefix}${diff} ${props.reactive.scale}`;
    }

    get positionStyle() {
        const { position } = this.props.reactive;
        const style = [`top:${position.top}px`];
        if ("left" in position) {
            style.push(`left:${position.left}px`);
        } else {
            style.push(`right:${position.right}px`);
        }
        return style.join(";");
    }
}
