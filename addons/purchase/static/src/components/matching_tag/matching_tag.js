import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class MatchingTag extends Component {
    static props = { ...standardFieldProps };
    static template = "purchase.MatchingTag";

    get colorClass() {
        if (this.matchValue) {
            return `o_tag_color_${parseInt(this.matchValue) % 12}`;
        } else {
            return "";
        }
    }

    get matchValue() {
        return this.props.record.data[this.props.name];
    }

    get canDisplayTag() {
        return this.matchValue && this.props.record.data.display_matching_tag;
    }
}

registry.category("fields").add("matching_tag", {
    component: MatchingTag,
    fieldDependencies: [{ name: "display_matching_tag", type: "boolean" }],
});
