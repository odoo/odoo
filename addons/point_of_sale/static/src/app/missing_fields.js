import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

// In pos we are not loading all the assests that the web views might need
// so this is a workaround such that we don't have console warnings

class DefaultField extends Component {
    static template = xml``;
}

class SalesPersonField extends Component {
    static template = xml`
        <span t-if="this.props.record?.data?.[this.props.name]">
            <t t-out="this.props.record?.data?.[this.props.name]?.display_name"/>
        </span>`;
}
registry.category("fields").add("list.many2one_avatar_user", { component: SalesPersonField });
registry.category("fields").add("list.list_activity", { component: DefaultField });
