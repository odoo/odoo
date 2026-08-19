import { Component, proxy, usePlugin, useProps } from "@odoo/owl";
import { router } from "@web/core/browser/router";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Setting } from "@web/views/form/setting/setting";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { SettingsBlock } from "@web/webclient/settings_form_view/settings/settings_block";

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
    props = useProps({
        ...standardWidgetProps,
    });

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        this.action = useService("action");
        this.isDemoDataActive = proxy({ value: true });
        useService("lazy_session").getValue("is_demo", (v) => (this.isDemoDataActive.value = !!v));
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
