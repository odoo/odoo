import { Component, useState, validate } from "@odoo/owl";

export class Toolbar extends Component {
    static template = "html_editor.Toolbar";
    static props = {
        class: { type: String, optional: true },
        toolbar: {
            type: Object,
            shape: {
                getSelection: Function,
                focusEditable: Function,
                buttonGroups: {
                    type: Array,
                    element: {
                        type: Object,
                        shape: {
                            id: String,
                            buttons: {
                                type: Array,
                                element: {
                                    type: Object,
                                    validate: (button) => {
                                        const base = {
                                            id: String,
                                            groupId: String,
                                            title: { type: [String, Function] },
                                            isAvailable: { type: Function, optional: true },
                                            isDisabled: { type: Function, optional: true },
                                            namespaces: { type: Array, element: String },
                                        };
                                        if (button.Component) {
                                            validate(button, {
                                                ...base,
                                                Component: Function,
                                                props: { type: Object, optional: true },
                                            });
                                        } else {
                                            validate(button, {
                                                ...base,
                                                run: Function,
                                                icon: { type: String, optional: true },
                                                text: { type: String, optional: true },
                                                isActive: { type: Function, optional: true },
                                            });
                                        }
                                        return true;
                                    },
                                },
                            },
                        },
                    },
                },
                state: {
                    type: Object,
                    shape: {
                        buttonsActiveState: Object,
                        buttonsDisabledState: Object,
                        buttonsAvailableState: Object,
                        buttonsTitleState: Object,
                        namespace: {
                            type: String,
                            optional: true,
                        },
                    },
                },
            },
        },
    };

    setup() {
        this.state = useState(this.props.toolbar.state);
    }

    getFilteredButtonGroups() {
        let buttonGroups = this.props.toolbar.buttonGroups;
        // Filter by namespace
        buttonGroups = buttonGroups.map((group) => ({
            ...group,
            buttons: group.buttons.filter((b) => b.namespaces.includes(this.state.namespace)),
        }));
        // Filter out buttons that are not available
        buttonGroups = buttonGroups.map((group) => ({
            ...group,
            buttons: group.buttons.filter((button) => this.state.buttonsAvailableState[button.id]),
        }));
        // Filter out groups left empty
        return buttonGroups.filter((group) => group.buttons.length > 0);
    }

    onButtonClick(button) {
        button.run();
        this.props.toolbar.focusEditable();
    }
}

export const toolbarButtonProps = {
    title: [String, Function],
    getSelection: Function,
};
