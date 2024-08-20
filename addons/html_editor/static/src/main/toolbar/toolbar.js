import { Component, useState, validate } from "@odoo/owl";

export class Toolbar extends Component {
    static template = "html_editor.Toolbar";
    static props = {
        class: { type: String, optional: true },
        toolbar: {
            type: Object,
            shape: {
                dispatch: Function,
                getSelection: Function,
                buttonGroups: {
                    type: Array,
                    element: {
                        type: Object,
                        shape: {
                            id: String,
                            sequence: Number,
                            namespace: { type: String, optional: true },
                            buttons: {
                                type: Array,
                                element: {
                                    type: Object,
                                    validate: (button) => {
                                        const base = {
                                            id: String,
                                            category: String,
                                            name: String,
                                            inherit: { type: String, optional: true },
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
                                                action: Function,
                                                icon: { type: String, optional: true },
                                                text: { type: String, optional: true },
                                                isFormatApplied: { type: Function, optional: true },
                                                hasFormat: { type: Function, optional: true },
                                                isAvailable: { type: Function, optional: true },
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
}

export const toolbarButtonProps = {
    name: String,
    dispatch: Function,
    getSelection: Function,
};
