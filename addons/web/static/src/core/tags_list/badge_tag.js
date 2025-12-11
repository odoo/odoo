import { Component } from "@odoo/owl";
import { mergeClasses } from "@web/core/utils/classname";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class BadgeTag extends Component {
    static template = "web.BadgeTag";
    static props = {
        color: { type: Number, optional: true },
        cssClass: { type: [String, Object], optional: true },
        onClick: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        ref: { optional: true },
        slots: { optional: true },
        text: { type: String, optional: true },
        tooltip: { type: String, optional: true },
    };
    static defaultProps = {
        color: 0,
    };

    get tagColorClass() {
        return `o_tag_color_${this.props.color}`;
    }

    get cssClass() {
        return mergeClasses(
            `o_badge badge rounded-pill lh-1 ${this.tagColorClass}`,
            { "cursor-pointer": this.props.onClick },
            this.props.cssClass
        );
    }

    setup() {
        useForwardRefToParent("ref");
    }
}
