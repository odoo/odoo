/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SettingsBlock } from "../settings/settings_block";
import { Setting } from "../settings/setting";

import { Component, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

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
ResConfigDevTool.components = {
    SettingsBlock,
    Setting,
};
ResConfigDevTool.props = {
    ...standardWidgetProps,
};

registry.category("view_widgets").add("res_config_dev_tool", ResConfigDevTool);
