/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LazyComponent } from "@web/core/assets";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, xml } from "@odoo/owl";

class StudioActionLoader extends Component {
    static components = { LazyComponent };
    static template = xml`
        <LazyComponent bundle="'web_studio.studio_assets'" Component="'StudioClientAction'" props="props"/>
    `;
    static props = {
        ...standardActionServiceProps,
        props: { type: Object, optional: true },
        Component: { type: Function, optional: true },
    };
}
registry.category("actions").add("studio", StudioActionLoader);
