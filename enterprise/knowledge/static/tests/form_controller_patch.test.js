import { beforeEach, describe, test } from "@odoo/hoot";
import { assertSteps, contains, click, step } from "@mail/../tests/mail_test_helpers";
import { onRpc, serverState, mountView } from "@web/../tests/web_test_helpers";
import { defineKnowledgeModels } from "@knowledge/../tests/knowledge_test_helpers";

describe.current.tags("desktop");
defineKnowledgeModels();

beforeEach(() => {
    onRpc("knowledge.article", "get_user_sorted_articles", () => []);
    onRpc("knowledge.article", "has_access", () => true);
    onRpc("res.partner", "web_save", () => step("save"));
});

test("can search for article on existing record", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: serverState.partnerId,
    });
    await contains(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette", { count: 0 });

    await click(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette");
    await assertSteps([]);
});

test("can search for article when creating valid record", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
    });
    await contains(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette", { count: 0 });

    await click(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette");
    await assertSteps(["save"]);
});

test("cannot search for article when creating invalid record", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        arch: /* xml */ `
            <form string="Partners">
                <sheet>
                    <field name="name" required="1" />
                </sheet>
                <chatter/>
            </form>
        `,
    });
    await contains(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette", { count: 0 });

    await click(".o_control_panel_navigation .o_knowledge_icon_search");
    await contains(".o_command_palette", { count: 0 });
    await assertSteps([]);
});
