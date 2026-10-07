import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";
import { contains, getService, switchView } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test('shortcut widget displays the appropriate "::" icon across views', async () => {
    const pyEnv = await startServer();
    pyEnv["mail.canned.response"].create([{ source: "hello" }]);
    await start();
    await getService("action").doAction({
        res_model: "mail.canned.response",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
            [false, "kanban"],
        ],
    });
    const selector = `div[name='source']`;

    await waitFor(`.o_control_panel_navigation .o_cp_switch_buttons:count(1)`);
    await waitFor(`.o_switch_view:count(2)`);

    await waitFor(".o_list_view .o_content:count(1)");
    await waitFor(`${selector}:text(':: hello'):count(1)`);

    await switchView("kanban");
    await waitFor(".o_kanban_view .o_content:count(1)");
    await waitFor(`${selector}:text(':: hello'):count(1)`);
    await contains(".o_control_panel_main_buttons .o-kanban-button-new:count(1)").click();
    await waitFor(`.o_form_view .o_content:count(1)`);
    await waitFor(`${selector} input[type='text']:count(1)`);
    await waitFor(`${selector}:text('::'):count(1)`);
});
