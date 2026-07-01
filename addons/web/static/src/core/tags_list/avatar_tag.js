import { Component, signal } from "@odoo/owl";

export class AvatarTag extends Component {
    static template = "web.AvatarTag";
    static props = {
        cssClass: { type: [String, Object], optional: true },
        imageUrl: { type: String },
        onAvatarClick: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        slots: { optional: true },
        text: { type: String, optional: true },
        tooltip: { type: String, optional: true },
    };

    ref = signal.ref();

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
