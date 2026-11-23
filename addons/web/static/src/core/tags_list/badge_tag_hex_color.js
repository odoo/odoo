import { t } from "@odoo/owl";
import { BadgeTag } from "./badge_tag";

export class BadgeTagHexColor extends BadgeTag {
    static hexRegex = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
    static template = "web.BadgeTagHexColor";
    static colorType = t.string().optional("");

    get hexColor() {
        const hexColor = this.color.color;
        return BadgeTagHexColor.hexRegex.test(hexColor) ? hexColor : null;
    }

    get tagColorClass() {
        return this.hexColor ? "o_tag_hex_color" : "o_tag_color_0";
    }
}
