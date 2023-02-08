/** @odoo-module */

import { registry } from "@web/core/registry";

import { ResConfigDevTool } from "@web/webclient/settings_form_view/widgets/res_config_dev_tool";

/**
 * Override of the widget in the settings that handles the "Developer Tools" section.
 * Provides a button to download XSD files for XML validation.
 */
class ResConfigDevToolDownloadXsd extends ResConfigDevTool {
    static template = "res_config_dev_tool";
    /**
     * Downloads every XSD file, based on installed localisations.
     */
    onClickDownloadXSD() {
        this.action.doAction("account.action_download_xsd");
    }
}

const resConfigDevToolDownloadXsd = {
    component: ResConfigDevToolDownloadXsd,
};

registry.category("view_widgets").add("res_config_dev_tool", resConfigDevToolDownloadXsd, {force: true});
