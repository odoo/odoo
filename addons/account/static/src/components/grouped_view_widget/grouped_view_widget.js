/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class ListItem extends Component {}
ListItem.template = "account.GroupedItemTemplate";
ListItem.props = ["item_vals", "options"];

class ListGroup extends Component {}
ListGroup.template = "account.GroupedItemsTemplate";
ListGroup.components = { ListItem };
ListGroup.props = ["group_vals", "options"];

class ShowGroupedList extends Component {
    getValue() {
        const value = this.props.record.data[this.props.name];
        return value
            ? JSON.parse(value)
            : { groups_vals: [], options: { discarded_number: "", columns: [] } };
    }
}
ShowGroupedList.template = "account.GroupedListTemplate";
ShowGroupedList.components = { ListGroup };

registry.category("fields").add("grouped_view_widget", {
    component: ShowGroupedList,
});
