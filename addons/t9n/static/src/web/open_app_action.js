import { Component, xml } from "@odoo/owl";

import { App } from "@t9n/core/app";

import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Wraps the application root, allowing us to open the application as a result
 * of a call to the "t9n.open_app" client action.
 */
export class OpenApp extends Component {
    static components = { App };
    static props = { ...standardActionServiceProps };
    static template = xml`<App/>`;
}

registry.category("actions").add("t9n.open_app", OpenApp);
