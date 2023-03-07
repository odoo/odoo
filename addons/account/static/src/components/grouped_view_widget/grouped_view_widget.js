/** @odoo-module */

import { registry } from "@web/core/registry";

const { Component, onWillUpdateProps } = owl;

class ListItem extends Component {}
ListItem.template = "account.GroupedItemTemplate";
ListItem.props = ["item_vals", "options"];

class ListGroup extends Component {}
ListGroup.template = "account.GroupedItemsTemplate";
ListGroup.components = { ListItem };
ListGroup.props = ["group_vals", "options"];

class ShowGroupedList extends Component {
    setup() {
        this.formatData(this.props);
        onWillUpdateProps((nextProps) => this.formatData(nextProps));
    }

    formatData(props) {
        this.data = props.record.data[props.name]
            ? JSON.parse(props.record.data[props.name])
            : { groups_vals: [], options: { discarded_number: "", columns: [] } };
    }
}
ShowGroupedList.template = "account.GroupedListTemplate";
ShowGroupedList.components = { ListGroup };

registry.category("fields").add("grouped_view_widget", {
    component: ShowGroupedList,
});
