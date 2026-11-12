import { Plugin, useListener, usePlugin } from "@odoo/owl";
import { rpcBus } from "@web/core/network/rpc";
import { UPDATE_METHODS } from "@web/core/orm_plugin";
import { services } from "@web/core/services";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { MenuPlugin } from "./menus/menu_plugin";

// reload the page if changes are being done to `res.company`

export class ReloadCompanyPlugin extends Plugin {
    action = usePlugin(ActionPlugin);
    menus = usePlugin(MenuPlugin);

    #noReloadFields = {
        home_font_color: true,
        use_menu_colors: true,
        menu_background_color: true,
        menu_font_color: true,
        background_image: true,
    };

    setup() {
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.company" && UPDATE_METHODS.includes(method)) {
                if (method === "web_save") {
                    const writtenFields = Object.keys(data.params.args[1]);
                    if (writtenFields.every((f) => this.#noReloadFields[f])) {
                        this.menus.reload();
                        return;
                    }
                }
                if (!window.localStorage.getItem("running_tour")) {
                    this.action.doAction("reload_context");
                }
            }
        });
    }
}

services.add(ReloadCompanyPlugin);
