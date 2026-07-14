import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SettingsBlock } from "../settings/settings_block";
import { Setting } from "../../../views/form/setting/setting";

import { Component, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { router } from "@web/core/browser/router";

/**
 * Widget in the settings that handles the "Developer Tools" section.
 * Can be used to enable/disable the debug modes.
 * Can be used to load the demo data.
 */
export class ResConfigDevTool extends Component {
    static template = "res_config_dev_tool";
    static components = {
        SettingsBlock,
        Setting,
    };
    static props = {
        ...standardWidgetProps,
    };

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

    activateDebug(value) {
        router.pushState({ debug: value }, { reload: true });
    }

    /**
     * Forces demo data to be installed in a database without demo data installed.
     */
    onClickForceDemo() {
        this.action.doAction("base.demo_force_install_action");
    }
}

export const resConfigDevTool = {
    component: ResConfigDevTool,
};

registry.category("view_widgets").add("res_config_dev_tool", resConfigDevTool);
