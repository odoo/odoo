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

function transformButtonClasses(givenClasses = [], defaultRank) {
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
        classes.push(defaultRank || "btn-secondary");
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

export class ViewButton extends Component {
    setup() {
        const classes = transformButtonClasses(this.props.classes, this.props.defaultRank);
        const { name, type, special, debounce } = this.props.clickParams;
        this.disabled = !name && !type && !special;
        if (this.props.size) {
            classes.push(`btn-${this.props.size}`);
        }
        this.classes = classes.join(" ");

        if (this.props.icon) {
            this.icon = iconFromString(this.props.icon);
        }
        if (debounce) {
            this.onClick = debounceFn(this.onClick.bind(this), debounce, true);
        }
    }

    onClick() {
        this.env.onClickViewButton({
            clickParams: this.props.clickParams,
            record: this.props.record,
        });
    }
}
ViewButton.template = "views.ViewButton";
ViewButton.defaultProps = {
    clickParams: {},
};
