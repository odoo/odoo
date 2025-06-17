import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "../standard_widget_props";

import { Component } from "@odoo/owl";

/**
 * This widget adds a ribbon on the top right side of the form
 *
 *      - You can specify the text with the title prop.
 *      - You can specify the title (tooltip) with the tooltip prop.
 *      - You can specify a background color for the ribbon with the bg_color prop
 *        using bootstrap classes :
 *        (bg-primary, bg-secondary, bg-success, bg-danger, bg-warning, bg-info,
 *        bg-light, bg-dark, bg-white)
 *
 *        If you don't specify the bg_color prop the bg-success class will be used
 *        by default.
 */
export class RibbonWidget extends Component {
    static template = "web.Ribbon";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        text: { type: String },
        title: { type: String, optional: true },
        bgClass: { type: String, optional: true },
    };
    static defaultProps = {
        title: "",
        bgClass: "text-bg-success",
    };

    get classes() {
        let classes = this.props.bgClass;
        if (this.props.text.length > 15) {
            classes += " o_small";
        } else if (this.props.text.length > 10) {
            classes += " o_medium";
        }
        return classes;
    }
}

export const ribbonWidget = {
    component: RibbonWidget,
    extractProps: ({ attrs }) => ({
        text: attrs.title || attrs.text,
        title: attrs.tooltip,
        bgClass: attrs.bg_color,
    }),
    supportedAttributes: [
        {
            label: _t("Title"),
            name: "title",
            type: "string",
        },
        {
            label: _t("Background color"),
            name: "bg_color",
            type: "string",
        },
        {
            label: _t("Tooltip"),
            name: "tooltip",
            type: "string",
        },
    ],
};

registry.category("view_widgets").add("web_ribbon", ribbonWidget);
