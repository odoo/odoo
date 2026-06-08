import { t } from "@odoo/owl";
import { BadgeTag } from "./badge_tag";

export class BadgeTagDot extends BadgeTag {
    static hexRegex = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
    static template = "web.BadgeTagDot";
    static colorType = t.string().optional("");

    get dotColor() {
        const dotColor = this.color.color;
        return BadgeTagDot.hexRegex.test(dotColor) ? dotColor : null;
    }

    get tagColorClass() {
        return "";
    }
}
