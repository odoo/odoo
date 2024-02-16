import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class ListItem extends Component {
    static template = "account.GroupedItemTemplate";
    static props = ["item_vals", "options"];
}

class ListGroup extends Component {
    static template = "account.GroupedItemsTemplate";
    static components = { ListItem };
    static props = ["group_vals", "options"];
}

class ShowGroupedList extends Component {
    static template = "account.GroupedListTemplate";
    static components = { ListGroup };
    static props = {...standardFieldProps};
    getValue() {
        const value = this.props.record.data[this.props.name];
        return value
            ? JSON.parse(value)
            : { groups_vals: [], options: { discarded_number: "", columns: [] } };
    }
}

registry.category("fields").add("grouped_view_widget", {
    component: ShowGroupedList,
});
