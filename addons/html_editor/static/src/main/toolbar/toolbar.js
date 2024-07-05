import { Component, useState } from "@odoo/owl";

export class Toolbar extends Component {
    static template = "html_editor.Toolbar";
    static props = {
        class: { type: String, optional: true },
        toolbar: {
            type: Object,
            shape: {
                dispatch: Function,
                getSelection: Function,
                // TODO: more specific prop validation for buttons after its format has been defined.
                buttonGroups: Array,
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
