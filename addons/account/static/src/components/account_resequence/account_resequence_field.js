import { registry } from "@web/core/registry";
import { Component, t, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class ChangeLine extends Component {
    static template = "account.ResequenceChangeLine";

    props = useProps({
        changeLine: t.any(),
        ordering: t.any(),
    });
}

class ShowResequenceRenderer extends Component {
    static template = "account.ResequenceRenderer";
    static components = { ChangeLine };

    props = useProps(standardFieldProps);

    getValue() {
        const value = this.props.record.data[this.props.name];
        return value ? JSON.parse(value) : { changeLines: [], ordering: "date" };
    }
}

registry.category("fields").add("account_resequence_widget", {
    component: ShowResequenceRenderer,
});
