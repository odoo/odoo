/** @odoo-module **/

const { Component, useState } = owl;

export class CustomGroupByItem extends Component {
    setup() {
        this.state = useState({});
        if (this.props.fields.length) {
            this.state.fieldName = this.props.fields[0].name;
        }
    }

    onApply() {
        this.trigger("add-custom-group", { fieldName: this.state.fieldName });
    }
}

CustomGroupByItem.template = "web.CustomGroupByItem";
