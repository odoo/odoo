/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

/**
 * Widget in the settings that handles the "Developer Tools" section.
 * Can be used to enable/disable the debug modes.
 * Can be used to load the demo data.
 */
class ResConfigDevTool extends Component {
    setup() {
        this.isDebug = Boolean(odoo.debug);
        this.isAssets = odoo.debug.includes("assets");
        this.isTests = odoo.debug.includes("tests");

        this.action = useService("action");
        this.demo = useService("demo_data");

        onWillStart(async () => {
            this.isDemoDataActive = await this.demo.isDemoDataActive();
        });
    }

    /**
     * Forces demo data to be installed in a database without demo data installed.
     */
    onClickForceDemo() {
        this.action.doAction("base.demo_force_install_action");
    }
}

ResConfigDevTool.template = "res_config_dev_tool";

registry.category("view_widgets").add("res_config_dev_tool", ResConfigDevTool);
