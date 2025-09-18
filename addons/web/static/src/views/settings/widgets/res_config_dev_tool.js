// @ts-check

/** @module @web/views/settings/widgets/res_config_dev_tool - Developer Tools settings widget for toggling debug modes and installing demo data */

import { Component, onWillStart } from "@odoo/owl";
import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Setting } from "@web/views/form/setting/setting";
import { SettingsBlock } from "@web/views/settings/settings/settings_block";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

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

    /** Initialize debug state flags and load demo data status. */
    setup() {
        /** @type {boolean} */
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
     * Activate or change the debug mode and reload the page.
     * @param {string} value - Debug mode value (e.g., "1", "assets", "tests")
     */
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
