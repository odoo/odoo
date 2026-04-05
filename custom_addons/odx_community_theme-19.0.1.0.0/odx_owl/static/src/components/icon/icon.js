/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { ICON_PATHS } from "./icon_data";

export class Icon extends Component {
    static template = "odx_owl.Icon";
    static props = {
        name: { type: String, required: true },
        size: { type: Number, optional: true },
        strokeWidth: { type: Number, optional: true },
        className: { type: String, optional: true },
        color: { type: String, optional: true },
    };
    static defaultProps = {
        size: 24,
        strokeWidth: 2,
        className: "",
        color: "currentColor",
    };

    get classes() {
        return cn("odx-icon", this.props.className);
    }

    get paths() {
        return ICON_PATHS[this.props.name] || ICON_PATHS["box"] || [
            { type: "path", d: "M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" },
            { type: "path", d: "m3.3 7 8.7 5 8.7-5" },
            { type: "path", d: "M12 22V12" },
        ];
    }
}
