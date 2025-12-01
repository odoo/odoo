import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

registry.category("actions").add("toolbar_send_mass_mail", async (env, action) => {
    const is_mailing_user = await user.hasGroup("mass_mailing.group_mass_mailing_user");
    if (!is_mailing_user) {
        return "mail.action_partner_mass_mail";
    }
    const domain = [["model", "=", action.context.active_model]];
    const activeModelId = await env.services.orm.search("ir.model", domain, { limit: 1 });
    const context = { default_mailing_model_id: activeModelId[0] };
    if (action.context.active_model == "mailing.list") {
        context.default_contact_list_ids = action.context.active_ids;
    } else {
        context.default_mailing_domain = [["id", "in", action.context.active_ids]];
    }
    return {
        type: "ir.actions.act_window",
        res_model: "mailing.mailing",
        views: [[false, "form"]],
        view_mode: "form",
        target: "current",
        context: context,
    };
});
