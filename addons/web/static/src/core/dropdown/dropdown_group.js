import { Component, t, useProps, xml } from "@odoo/owl";
import { provideDropdownGroup } from "@web/core/dropdown/_behaviours/dropdown_group_hook";

export class DropdownGroup extends Component {
    static template = xml`<t t-call-slot="default"/>`;
    props = useProps({
        group: t.string().optional(),
        slots: t.object(),
    });

    setup() {
        provideDropdownGroup(this.props.group);
    }
}
