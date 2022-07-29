/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "../standard_widget_props";

const { Component } = owl;

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
class RibbonWidget extends Component {
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

RibbonWidget.template = "web.Ribbon";
RibbonWidget.props = {
    ...standardWidgetProps,
    text: { type: String },
    title: { type: String, optional: true },
    bgClass: { type: String, optional: true },
};
RibbonWidget.defaultProps = {
    title: "",
    bgClass: "bg-success",
};
RibbonWidget.extractProps = ({ attrs }) => {
    return {
        text: attrs.title || attrs.text,
        title: attrs.tooltip,
        bgClass: attrs.bg_color,
    };
};

registry.category("view_widgets").add("web_ribbon", RibbonWidget);
