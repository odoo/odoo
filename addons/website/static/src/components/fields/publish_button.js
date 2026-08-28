import { registry } from "@web/core/registry";
import { Component, useProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class PublishField extends Component {
    static template = "website.PublishField";
    props = useProps({ ...standardFieldProps });
}

registry.category("fields").add("website_publish_button", {
    component: PublishField,
});
