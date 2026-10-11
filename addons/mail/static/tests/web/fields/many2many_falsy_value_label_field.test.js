import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, getService, switchView } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("many2many_falsy_value_label widget displays `🔒 private` label across views", async () => {
    const pyenv = await startServer();
    pyenv["mail.canned.response"].create([{ source: "hello" }]);
    await start();
    await getService("action").doAction({
        res_model: "mail.canned.response",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    });
    await waitFor(".o_control_panel_navigation .o_cp_switch_buttons:count(1)");
    await waitFor(".o_switch_view:count(2)");
    await waitFor(".o_list_view .o_content:count(1)");
    await waitFor(".o-mail-Many2ManyFalsyValueLabelField:text('🔒 Private'):count(1)");
    await switchView("kanban");
    await waitFor(".o_kanban_view .o_content:count(1)");
    await waitFor(".o-mail-Many2ManyFalsyValueLabelField:text('🔒 Private'):count(1)");
    await contains(".o_control_panel_main_buttons .o-kanban-button-new:count(1)").click();
    await waitFor(".o_form_view .o_content:count(1)");
    await waitFor(".o-mail-Many2ManyFalsyValueLabelField input[placeholder='🔒 Private']:count(1)");
});
