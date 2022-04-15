/** @odoo-module */

import { debounce as debounceFn } from "@web/core/utils/timing";

const { Component } = owl;

const explicitRankClasses = [
    "btn-primary",
    "btn-secondary",
    "btn-link",
    "btn-success",
    "btn-info",
    "btn-warning",
    "btn-danger",
];

const odooToBootstrapClasses = {
    oe_highlight: "btn-primary",
    oe_link: "btn-link",
};

function iconFromString(iconString) {
    const icon = {};
    if (iconString.startsWith("fa-")) {
        icon.tag = "i";
        icon.class = `fa fa-fw o_button_icon ${iconString}`;
    } else {
        icon.tag = "img";
        icon.src = iconString;
    }
    return icon;
}

export class ViewButton extends Component {
    setup() {
        this.className = this.getButtonClassName();

        if (this.props.icon) {
            this.icon = iconFromString(this.props.icon);
        }
        const { debounce } = this.props.clickParams;
        if (debounce) {
            this.onClick = debounceFn(this.onClick.bind(this), debounce, true);
        }
    }

    get disabled() {
        const { name, type, special } = this.props.clickParams;
        return (!name && !type && !special) || this.props.disabled;
    }

    onClick() {
        this.env.onClickViewButton({
            clickParams: this.props.clickParams,
            record: this.props.record,
        });
    }

    getButtonClassName() {
        const classNames = [];
        let hasExplicitRank = false;
        for (let cls of this.props.className.split(" ")) {
            if (cls in odooToBootstrapClasses) {
                cls = odooToBootstrapClasses[cls];
            }
            classNames.push(cls);
            if (!hasExplicitRank && explicitRankClasses.includes(cls)) {
                hasExplicitRank = true;
            }
        }
        if (!hasExplicitRank) {
            classNames.push(this.props.defaultRank || "btn-secondary");
        }
        if (this.props.size) {
            classNames.push(`btn-${this.props.size}`);
        }
        return classNames.join(" ");
    }
}
ViewButton.template = "views.ViewButton";
ViewButton.props = [
    "record?",
    "className?",
    "clickParams?",
    "icon?",
    "defaultRank?",
    "disabled?",
    "size?",
    "title?",
    "string?",
    "slots?",
];
ViewButton.defaultProps = {
    className: "",
    clickParams: {},
};
