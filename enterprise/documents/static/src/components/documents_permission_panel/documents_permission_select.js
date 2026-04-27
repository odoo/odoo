/** @odoo-module **/

import { SelectMenu } from "@web/core/select_menu/select_menu";
import { Component } from "@odoo/owl";

export class DocumentsPermissionSelect extends Component {
    static defaultProps = {
        ariaLabel: "Document permission select",
        disabled: false,
    };
    static props = {
        ariaLabel: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        labelHelper: { type: String, optional: true },
        options: Array,
        onChange: { type: Function, optional: true },
        selectClass: { type: String, optional: true },
        showFeedbackChange: { type: Boolean, optional: true },
        value: [String, Number, Boolean],
        noEditorMessage: { type: String, optional: true },
    };
    static template = "documents.PermissionSelect";

    get selectClass() {
        return `${
            this.props.selectClass ? this.props.selectClass : this.props.label ? "w-75" : "w-50"
        } ${this.props.showFeedbackChange ? "border-primary" : ""}`;
    }
}

export class DocumentsPermissionSelectMenu extends SelectMenu {
    static defaultProps = {
        ...super.defaultProps,
        hasColor: false,
    };
    static props = {
        ...super.props,
        buttonText: { type: String, optional: true },
        hasColor: { type: Boolean, optional: true },
        onOpen: { type: Function, optional: true },
    };
    static template = "documents.PermissionSelectMenu";

    onStateChanged(open) {
        super.onStateChanged(open);
        if (open) {
            this.menuRef.el.querySelector("input").focus();
            this.props.onOpen?.();
        }
    }

    get multiSelectChoices() {
        if (this.props.hasColor) {
            const choices = [
                ...this.props.choices,
                ...this.props.groups.flatMap((g) => g.choices),
            ].filter((c) => this.props.value.includes(c.value));
            return choices.map((c) => {
                return {
                    id: c.value,
                    text: c.label,
                    colorIndex: c.colorIndex,
                    onDelete: () => {
                        const values = [...this.props.value];
                        values.splice(values.indexOf(c.value), 1);
                        this.props.onSelect(values);
                    },
                };
            });
        }
        return super.multiSelectChoices;
    }
}
