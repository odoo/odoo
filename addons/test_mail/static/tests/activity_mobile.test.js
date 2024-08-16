import { describe, expect, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { openView, start, startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("mobile");
defineTestMailModels();

test("horizontal scroll applies only to the content, not to the whole controller", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.activity.type"].create([
        { name: "Email" },
        { name: "Call" },
        { name: "Upload document" },
    ]);
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    const o_view_controller = document.querySelector(".o_view_controller");
    const o_content = o_view_controller.querySelector(".o_content");
    const o_cp_item = document.querySelector(".o_breadcrumb .active");
    const initialXCpItem = o_cp_item.getBoundingClientRect().x;
    const o_header_cell = o_content.querySelector(".o_activity_type_cell");
    const initialXHeaderCell = o_header_cell.getBoundingClientRect().x;
    expect(o_view_controller).toHaveClass("o_action_delegate_scroll");
    expect(o_view_controller).toHaveStyle({ overflow: "hidden" });
    expect(o_content).toHaveStyle({ overflow: "auto" });
    expect(o_content.scrollLeft).toBe(0);

    o_content.scrollLeft = 100;
    expect(o_content.scrollLeft).toBe(100);
    expect(o_header_cell.getBoundingClientRect().x).toBeLessThan(initialXHeaderCell);
    expect(o_cp_item).toHaveRect({ x: initialXCpItem });
});
