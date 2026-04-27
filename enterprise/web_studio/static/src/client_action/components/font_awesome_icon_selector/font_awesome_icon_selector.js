/** @odoo-module */
import { Component } from "@odoo/owl";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { getFontAwesomeIcons } from "@web_studio/utils";

export class FontAwesomeIconSelector extends Component {
    static defaultProps = {
        className: "",
        menuClassName: "",
    };
    static template = "web_studio.FontAwesomeIconSelector";
    static props = {
        className: { type: String, optional: true },
        menuClassName: { type: String, optional: true },
        value: { type: String },
        onSelect: { type: Function, optional: true },
        slots: true,
    };
    static components = { SelectMenu };

    setup() {
        this.ICONS = getFontAwesomeIcons();
    }

    get iconChoices() {
        return this.ICONS.map((icon) => {
            return {
                label: icon.searchTerms.join(" "),
                value: icon.className,
            };
        });
    }

    getIconTooltip(value) {
        return this.ICONS.find((icon) => icon.className === value).tooltip;
    }
}
