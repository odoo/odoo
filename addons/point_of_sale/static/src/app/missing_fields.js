import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

// In pos we are not loading all the assests that the web views might need
// so this is a workaround such that we don't have console warnings

class DefaultField extends Component {
    static template = xml``;
    static props = ["*"];
}

class SalesPersonField extends Component {
    static template = xml`
        <span t-if="props.record.data[props.name]">
            <t t-esc="props.record.data[props.name].display_name"/>
        </span>`;
    static props = ["*"];
}
registry.category("fields").add("list.many2one_avatar_user", { component: SalesPersonField });
registry.category("fields").add("list.list_activity", { component: DefaultField });
