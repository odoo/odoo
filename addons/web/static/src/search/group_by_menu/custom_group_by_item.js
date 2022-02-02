/** @odoo-module **/

const { Component, useState } = owl;

export class CustomGroupByItem extends Component {
    setup() {
        this.state = useState({});
        if (this.props.fields.length) {
            this.state.fieldName = this.props.fields[0].name;
        }
    }
}

CustomGroupByItem.template = "web.CustomGroupByItem";
