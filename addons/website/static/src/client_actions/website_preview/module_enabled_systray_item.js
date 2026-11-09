import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, onWillStart, proxy, useProps } from "@odoo/owl";

const websiteSystrayRegistry = registry.category("website_systray");

export class ModuleEnabledSystrayItem extends Component {
    static template = "website.ModuleEnabledSystrayItem";
    static components = { CheckBox };
    props = useProps({});

    setup() {
        this.website = useService("website");
        this.orm = useService("orm");
        this.state = proxy({ moduleId: false, moduleName: "", enabled: true, processing: false });
        onWillStart(() => this.updateState());
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", () => this.updateState());
    }

    get label() {
        // e.g. "eCommerce Enabled", "Blog Enabled"
        return _t("%s Enabled", this.state.moduleName);
    }

    async updateState() {
        if (!this.website.currentWebsite || !this.website.contentWindow) {
            this.state.moduleId = false;
            return;
        }
        const info = await this.orm.call("website", "get_module_toggle_info", [
            [this.website.currentWebsite.id],
            this.website.currentLocation,
        ]);
        this.state.moduleId = info ? info.id : false;
        this.state.moduleName = info ? info.name : "";
        this.state.enabled = info ? info.enabled : true;
    }

    async toggle() {
        if (this.state.processing || !this.state.moduleId) {
            return;
        }
        this.state.processing = true;
        const enable = !this.state.enabled;
        try {
            // disabled_module_ids: unlink (3) to enable, link (4) to disable.
            await this.orm.write("website", [this.website.currentWebsite.id], {
                disabled_module_ids: [[enable ? 3 : 4, this.state.moduleId]],
            });
            this.state.enabled = enable;
            this.website.contentWindow.location.reload();
        } finally {
            this.state.processing = false;
        }
    }
}
