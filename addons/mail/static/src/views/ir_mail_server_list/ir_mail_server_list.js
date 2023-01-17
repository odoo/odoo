/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class IrMailServerController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async onLinkClick() {
        await this.actionService.doAction({
            name: _t("Configure a Server"),
            type: "ir.actions.act_window",
            res_model: "mail.server.configurator",
            target: "new",
            views: [[false, "form"]],
        });
    }
}

export const irMailServerListView = {
    ...listView,
    Controller: IrMailServerController,
    buttonTemplate: "IrMailServer.buttons",
};

registry.category("views").add("ir_mail_server_list", irMailServerListView);
