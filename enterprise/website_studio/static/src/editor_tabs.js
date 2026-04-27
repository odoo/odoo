import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const MODEL_PAGE_HELP = _t(markup(`
    <p class="o_view_nocontent_empty_folder">
        Create a new model page
    </p>
    <p>
        Publish everything on your websites
        then customize the pages
        using the power of the Website app
    </p>
`));

registry.category("web_studio.editor_tabs").add("website", {
    name: _t("Model Pages"),
    action: (env) => {
        const { editedAction } = env.services.studio;
        const context = {
            default_model: editedAction.res_model,
            search_default_model: editedAction.res_model,
            default_page_type: "listing",
            default_website_published: true,
            default_use_menu: true,
            default_auto_single_page: true,
            form_view_ref: "website_studio.website_controller_page_form_dialog",
            "website_studio.create_page": true,
        }
        return {
            type: "ir.actions.act_window",
            res_model: "website.controller.page",
            name: _t("Model Pages"),
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            context,
            help: MODEL_PAGE_HELP,
        }
    },
});
