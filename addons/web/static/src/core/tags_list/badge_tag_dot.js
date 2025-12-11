import { BadgeTag } from "./badge_tag";

export class BadgeTagDot extends BadgeTag {
    static hexRegex = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
    static template = "web.BadgeTagDot";
    static defaultProps = {
        color: "",
    };
    static props = {
        ...BadgeTag.props,
        color: { type: String, optional: true },
    };

    get dotColor() {
        const dotColor = this.props.color;
        return BadgeTagDot.hexRegex.test(dotColor) ? dotColor : null;
    }

    get tagColorClass() {
        return "";
    }
}
