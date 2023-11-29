/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class LazyTestComponent extends Component {
    static template = "test_assetsbundle.LazyTestComponent";
    static props = ["*"];
    setup() {
        this.props.onCreated();
    }
}

registry.category("lazy_components").add("LazyTestComponent", LazyTestComponent);
