import {
    click,
    contains,
    defineMailModels,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { getService, switchView } from "@web/../tests/web_test_helpers";

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

    await contains(`.o_control_panel_navigation .o_cp_switch_buttons`);
    await contains(`.o_switch_view`, { count: 2 });

    await contains(".o_list_view .o_content");
    await contains(selector, { text: "::hello" });

    await switchView("kanban");
    await contains(".o_kanban_view .o_content");
    await contains(selector, { text: "::hello" });

    await click(".o_control_panel_main_buttons .o-kanban-button-new");
    await contains(`.o_form_view .o_content`);
    await contains(`${selector} input[type='text']`);
    await contains(selector, { text: "::" });
});
