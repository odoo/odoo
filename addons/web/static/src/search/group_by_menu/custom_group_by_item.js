/** @odoo-module **/

const { Component, hooks } = owl;
const { useState } = hooks;

export class CustomGroupByItem extends Component {
    setup() {
        this.state = useState({});
        if (this.props.fields.length) {
            this.state.fieldName = this.props.fields[0].name;
        }
    }

    onApply(ev) {
        ev.detail.payload = this.state.fieldName;
    }
}

CustomGroupByItem.template = "web.CustomGroupByItem";
