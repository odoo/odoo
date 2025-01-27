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
                            namespace: { type: String, optional: true },
                            buttons: {
                                type: Array,
                                element: {
                                    type: Object,
                                    validate: (button) => {
                                        const base = {
                                            id: String,
                                            groupId: String,
                                            title: String,
                                            isAvailable: { type: Function, optional: true },
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
                                                isDisabled: { type: Function, optional: true },
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
        if (this.state.namespace) {
            const filteredGroups = this.props.toolbar.buttonGroups.filter(
                (group) => group.namespace === this.state.namespace
            );
            if (filteredGroups.length > 0) {
                return filteredGroups;
            }
        }
        return this.props.toolbar.buttonGroups.filter((group) => group.namespace === undefined);
    }

    onButtonClick(button) {
        button.run();
        this.props.toolbar.focusEditable();
    }
}

export const toolbarButtonProps = {
    title: String,
    getSelection: Function,
};
