import { Component, signal, t, useProps } from "@odoo/owl";

export const avatarTagProps = {
    cssClass: t.or([t.string(), t.object()]).optional(),
    imageUrl: t.string(),
    onAvatarClick: t.function().optional(),
    onDelete: t.function().optional(),
    slots: t.any().optional(),
    text: t.string().optional(),
    tooltip: t.string().optional(),
};

export class AvatarTag extends Component {
    static template = "web.AvatarTag";
    props = useProps(avatarTagProps);

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
