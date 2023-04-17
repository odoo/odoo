/** @odoo-module **/
import { Component, xml, useChildSubEnv } from "@odoo/owl";

export class DropdownGroup extends Component {
    static template = xml`<t t-slot="default"/>`;
    static props = {
        slots: Object,
    };

    setup() {
        useChildSubEnv({ dropdownGroup: new Set() });
    }
}
