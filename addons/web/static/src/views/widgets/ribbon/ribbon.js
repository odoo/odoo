// @ts-check

/** @module @web/views/widgets/ribbon/ribbon - Decorative ribbon on the top-right corner of a form view with configurable label and color */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Decorative ribbon on the top-right corner of a form view.
 *
 * Configurable via arch attributes:
 * - `title` / `text`: ribbon label
 * - `tooltip`: hover tooltip
 * - `bg_color`: Bootstrap background class (default: `text-bg-success`)
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

    /** @returns {string} CSS classes for the ribbon element, including size modifiers */
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
