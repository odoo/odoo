import { Component } from "@odoo/owl";

export const MODULE_STATUS = {
    NOT_INSTALLED: "NOT_INSTALLED",
    INSTALLING: "INSTALLING",
    FAILED_TO_INSTALL: "FAILED_TO_INSTALL",
    INSTALLED: "INSTALLED",
};

export class NewContentElement extends Component {
    static template = "website.NewContentElement";
    static props = {
        name: { type: String, optional: true },
        title: String,
        onClick: Function,
        status: { type: String, optional: true },
        moduleXmlId: { type: String, optional: true },
        slots: Object,
    };
    static defaultProps = {
        status: MODULE_STATUS.INSTALLED,
    };

    setup() {
        this.MODULE_STATUS = MODULE_STATUS;
    }

    onClick(ev) {
        this.props.onClick();
    }
}
