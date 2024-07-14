/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class EditableName extends Component {
    setup() {
        super.setup();
        this.state = useState({
            isEditing: false,
            name: "",
        });
    }

    rename() {
        this.state.isEditing = true;
        this.state.name = this.props.name;
    }

    save() {
        this.props.onChanged(this.state.name.trim());
        this.state.isEditing = false;
    }
}

EditableName.template = "spreadsheet_edition.EditableName";
EditableName.props = {
    name: String,
    displayName: String,
    onChanged: Function,
};
