import { t } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * The generic buttons of the tutorials, which aren't buttons of their view,
 * by name, with the selector of the element(s) doing them. The Python side
 * lists them with the types of view they can be used in, in
 * `web_tuto.step._get_generic_buttons`.
 */
const buttonRegistry = registry.category("web_tuto.buttons");
buttonRegistry.addValidation(t.string());

buttonRegistry
    .add(
        "new",
        ".o_control_panel :is([class*='_button_add']:not([class*='_button_add_']), .o-kanban-button-new, .o_form_button_create), .o_kanban_group .o_kanban_quick_add"
    )
    .add(
        "create",
        ".o_quick_create_folded .o_quick_create_button, .o_quick_create_unfolded .o_kanban_add"
    )
    .add("edit", ".o_kanban_quick_create .o_kanban_edit")
    .add("send", ".o-mail-Chatter-sendMessage")
    .add("log", ".o-mail-Chatter-logNote")
    .add("delete", ".o_cp_action_menus button[data-hotkey='u']");
