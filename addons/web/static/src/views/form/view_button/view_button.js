/** @odoo-module */

import { useListener } from "web.custom_hooks";

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

function transformButtonClasses(givenClasses = []) {
    const classes = [];

    let hasExplicitRank = false;
    for (let cls of givenClasses) {
        if (cls in odooToBootstrapClasses) {
            cls = odooToBootstrapClasses[cls];
        }
        classes.push(cls);
        if (!hasExplicitRank && explicitRankClasses.includes(cls)) {
            hasExplicitRank = true;
        }
    }

    if (!hasExplicitRank) {
        classes.push("btn-secondary");
    }

    return classes;
}

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

export class ViewButton extends owl.Component {
    setup() {
        const classes = transformButtonClasses(this.props.classes);
        if (this.props.size) {
            classes.push(`btn-${this.props.size}`);
        }
        this.classes = classes.join(" ");

        if (this.props.icon) {
            this.icon = iconFromString(this.props.icon);
        }

        if (this.props.onClick) {
            useListener("click", () => this.props.onClick());
        }

        if (this.props.data) {
            this.attData = {};
            for (const key in this.props.data) {
                this.attData[`data-${key}`] = this.props.data[key];
            }
        }
    }
}
ViewButton.template = "views.ViewButton";
