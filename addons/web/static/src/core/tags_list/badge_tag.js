import { Component, props, t } from "@odoo/owl";
import { mergeClasses } from "@web/core/utils/classname";
import { _t } from "@web/core/l10n/translation";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export const badgeTagProps = {
    cssClass: t.or([t.string(), t.object()]).optional(),
    onClick: t.function().optional(),
    onDelete: t.function().optional(),
    crossTooltip: t.string().optional(_t("Delete")),
    ref: t.any().optional(),
    slots: t.any().optional(),
    text: t.string().optional(),
    tooltip: t.string().optional(),
};

export class BadgeTag extends Component {
    static template = "web.BadgeTag";
    static colorType = t.number().optional(0);
    props = props(badgeTagProps);
    color = props({ color: this.constructor.colorType });

    get tagColorClass() {
        return `o_tag_color_${this.color.color}`;
    }

    get cssClass() {
        return mergeClasses(
            `o_badge badge rounded-pill ${this.tagColorClass}`,
            { "cursor-pointer": this.props.onClick },
            this.props.cssClass
        );
    }

    setup() {
        useForwardRefToParent("ref");
    }
}
