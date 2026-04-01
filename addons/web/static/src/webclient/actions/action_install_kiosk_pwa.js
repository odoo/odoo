import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "./action_service";

import { Component, onWillStart } from "@odoo/owl";

/**
 * Client action to use in a dialog to display the URL of a Kiosk, containing a
 * link to Install the corresponding PWA
 */
export class InstallKiosk extends Component {
    static template = "web.ActionInstallKioskPWA";
    static props = { ...standardActionServiceProps };

    setup() {
        this.resModel = this.props.action.res_model;
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        onWillStart(async () => {
            this.url = await this.orm.call(this.resModel, "get_kiosk_url", [
                this.props.action.context.active_id,
            ]);
        });
    }

    get appId() {
        return this.props.action.context.app_id || this.resModel;
    }

    get installURL() {
        return `/scoped_app?app_id=${this.appId}&path=${encodeURIComponent(
            this.url.replace(document.location.origin + "/", "")
        )}`;
    }
}

registry.category("actions").add("install_kiosk_pwa", InstallKiosk);
