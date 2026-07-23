import { usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ORM } from "@web/core/orm_plugin";
import { WhatIsPeppol } from "@account_peppol/components/peppol_info/peppol_info";

class WhatIsPdp extends WhatIsPeppol {
    static template = "l10n_fr_pdp.WhatIsPdp";
    orm = usePlugin(ORM);

    get shouldRegisterOnClose() {
        return this.props.action.context.action_on_activate.context?.res_config_settings_id;
    }

    async activate() {
        const action_on_activate = this.props.action.context.action_on_activate;
        const action = await this.orm.call("res.config.settings", "button_peppol_reregister", [
            action_on_activate.context.res_config_settings_id,
        ]);
        this.actionService.doAction({
            name: action.name,
            type: action.type,
            res_model: action.res_model,
            res_id: action.res_id,
            views: [[false, action.view_mode]],
            target: action.target,
            context: action_on_activate.context,
        });
    }
}

registry.category("actions").add("l10n_fr_pdp.what_is_pdp", WhatIsPdp);
