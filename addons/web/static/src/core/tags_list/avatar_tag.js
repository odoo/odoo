import { Component } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class AvatarTag extends Component {
    static template = "web.AvatarTag";
    static props = {
        cssClass: { type: [String, Object], optional: true },
        imageUrl: { type: String },
        onAvatarClick: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        ref: { type: Object, optional: true },
        slots: { optional: true },
        text: { type: String, optional: true },
        tooltip: { type: String, optional: true },
    };

    setup() {
        useForwardRefToParent("ref");
    }

    /**
     * @param {MouseEvent} ev
     */
    onAvatarClick(ev) {
        if (this.props.onAvatarClick) {
            ev.stopPropagation();
            ev.preventDefault();
            this.props.onAvatarClick(ev.target);
        }
    }
}
