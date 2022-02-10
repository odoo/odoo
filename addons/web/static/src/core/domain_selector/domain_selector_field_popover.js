/** @odoo-module **/

const { Component, onWillStart, useState } = owl;

export class DomainSelectorFieldPopover extends Component {
    setup() {
        this.state = useState({
            currentFields: {},
        });
        onWillStart(async () => {
            this.state.currentFields = await this.props.model.loadFields();
        });
    }
}
DomainSelectorFieldPopover.template = "web.DomainSelectorFieldPopover";
