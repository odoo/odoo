import { registry } from "@web/core/registry";
import { Component, t, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class ListItem extends Component {
    static template = "account.GroupedItemTemplate";
    props = useProps({
        item_vals: t.any(),
        options: t.any(),
    });
}

class ListGroup extends Component {
    static template = "account.GroupedItemsTemplate";
    static components = { ListItem };
    props = useProps({
        group_vals: t.any(),
        options: t.any(),
    });
}

class ShowGroupedList extends Component {
    static template = "account.GroupedListTemplate";
    static components = { ListGroup };
    props = useProps(standardFieldProps);
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
