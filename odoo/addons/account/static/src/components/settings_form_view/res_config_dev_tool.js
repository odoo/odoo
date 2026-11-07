/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ResConfigDevTool } from "@web/webclient/settings_form_view/widgets/res_config_dev_tool";

/**
 * Override of the widget in the settings that handles the "Developer Tools" section.
 * Provides a button to download XSD files for XML validation.
 */
class ResConfigDevToolDownloadXsd extends ResConfigDevTool {
    /**
     * Downloads every XSD file, based on installed localisations.
     */

    static template = "res_config_dev_tool";

    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }

    async onClickDownloadXSD() {
        await this.rpc("/web/dataset/call_kw/ir.attachment/action_download_xsd_files", {
            model: 'ir.attachment',
            method: 'action_download_xsd_files',
            args: [],
            kwargs: {}
        })
    }
}

const resConfigDevToolDownloadXsd = {
    component: ResConfigDevToolDownloadXsd,
};

registry.category("view_widgets").add("res_config_dev_tool", resConfigDevToolDownloadXsd, {force: true});
