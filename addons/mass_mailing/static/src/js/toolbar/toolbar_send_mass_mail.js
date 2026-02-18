import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

registry.category("actions").add("toolbar_send_mass_mail", async (env, action) => {
    const is_mailing_user = await user.hasGroup("mass_mailing.group_mass_mailing_user");
    if (!is_mailing_user) {
        return {
            type: "ir.actions.act_window",
            res_model: "mailing.mailing",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_composition_mode: "mass_mail",
                default_partner_to: "{{ object.id or '' }}",
                default_subtype_xmlid: "mail.mt_comment",
                default_reply_to_force_new: true,
            },
        };
    }
    const context = {
        default_mailing_model_name: action.context.active_model,
    };
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
