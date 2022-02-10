/** @odoo-module **/

const { Component, useState } = owl;

export class DomainSelectorFieldPopover extends Component {
    setup() {
        this.state = useState({
            currentFields: {},
        });
    }
    async willStart() {
        this.state.currentFields = await this.props.model.loadFields();
    }
}
DomainSelectorFieldPopover.template = "web.DomainSelectorFieldPopover";
