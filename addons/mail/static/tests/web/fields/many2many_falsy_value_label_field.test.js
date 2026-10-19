import {
    click,
    contains,
    defineMailModels,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { getService, switchView } from "@web/../tests/web_test_helpers";

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
    await contains(".o_control_panel_navigation .o_cp_switch_buttons");
    await waitFor(".o_switch_view:count(2)");
    await contains(".o_list_view .o_content");
    await contains(".o-mail-Many2ManyFalsyValueLabelField:text('🔒 Private')");
    await switchView("kanban");
    await contains(".o_kanban_view .o_content");
    await contains(".o-mail-Many2ManyFalsyValueLabelField:text('🔒 Private')");
    await click(".o_control_panel_main_buttons .o-kanban-button-new");
    await contains(".o_form_view .o_content");
    await contains(".o-mail-Many2ManyFalsyValueLabelField input[placeholder='🔒 Private']");
});
