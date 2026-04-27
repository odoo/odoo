/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LazyComponent } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, xml } from "@odoo/owl";

class StudioActionLoader extends Component {
    static components = { LazyComponent };
    static template = xml`
        <LazyComponent bundle="bundle" Component="'StudioClientAction'" props="props"/>
    `;
    static props = {
        ...standardActionServiceProps,
        props: { type: Object, optional: true },
        Component: { type: Function, optional: true },
    };
    setup() {
        this.bundle =
            cookie.get("color_scheme") === "dark"
                ? "web_studio.studio_assets_dark"
                : "web_studio.studio_assets";
    }
}
registry.category("actions").add("studio", StudioActionLoader);
