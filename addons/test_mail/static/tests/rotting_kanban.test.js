import { openKanbanView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { clickKanbanLoadMore, contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineTestMailModels();

const ROTTING_KANBAN_ARCH = `
    <kanban js_class="rotting_kanban" default_group_by="stage_id" limit="10">
        <progressbar field="name" colors="{}"/>
        <templates>
            <t t-name="card">
                <field name="name"/>
                <field name="is_rotting" invisible="1"/>
            </t>
        </templates>
    </kanban>`;

async function createRottingResources() {
    const pyEnv = await startServer();
    const [stageNewId, stageQualifId] = pyEnv["mail.test.rotting.stage"].create([
        { name: "New" },
        { name: "Qualified" },
    ]);
    pyEnv["mail.test.rotting.resource"].create([
        { name: "fresh 1", stage_id: stageNewId },
        { name: "fresh 2", stage_id: stageNewId },
        ...Array.from({ length: 15 }, (_, i) => ({
            name: `rotting ${i}`,
            stage_id: stageNewId,
            is_rotting: true,
        })),
        { name: "rotting qualified", stage_id: stageQualifId, is_rotting: true },
    ]);
}

const column = ".o_kanban_group:eq(0)";
const badge = `${column} .o_kanban_counter .o_mail_resource_rotting_bg`;
const secondBadge = ".o_kanban_group:eq(1) .o_kanban_counter .o_mail_resource_rotting_bg";
const rottingRecords = `${column} .o_kanban_record.oe_kanban_card_rotting`;
const freshRecords = `${column} .o_kanban_record:not(.oe_kanban_card_rotting)`;

test("rotting badge counts all rotting records and toggles a filter allowing to load more", async () => {
    await createRottingResources();
    onRpc("mail.test.rotting.resource", "web_read_group", ({ kwargs }) => {
        expect.step(`web_read_group ${kwargs.aggregates}`);
    });

    onRpc("mail.test.rotting.resource", "read_progress_bar", () => ({}));
    await start();
    await openKanbanView("mail.test.rotting.resource", { arch: ROTTING_KANBAN_ARCH });
    expect.verifySteps(["web_read_group is_rotting:sum"]);

    expect(`${column} .o_kanban_record`).toHaveCount(10);
    expect(freshRecords).toHaveCount(2);
    expect(badge).toHaveText("15");
    expect(secondBadge).toHaveText("1");

    await contains(badge).click();
    expect(column).toHaveClass("o_kanban_group_show_rotting");
    expect(rottingRecords).toHaveCount(10);
    expect(freshRecords).toHaveCount(0);

    await clickKanbanLoadMore(0);
    expect(rottingRecords).toHaveCount(15);
    expect(freshRecords).toHaveCount(0);
    expect(`${column} .o_kanban_load_more`).toHaveCount(0);
    expect(badge).toHaveText("15");

    await contains(badge).click();
    expect(column).not.toHaveClass("o_kanban_group_show_rotting");
    expect(freshRecords).toHaveCount(2);
    expect(badge).toHaveText("15");
    expect.verifySteps([]);
});

test("rotting badge is updated when moving a rotting record to another stage", async () => {
    await createRottingResources();
    onRpc("mail.test.rotting.resource", "web_read_group", () => {
        expect.step("web_read_group");
    });
    await start();
    await openKanbanView("mail.test.rotting.resource", { arch: ROTTING_KANBAN_ARCH });
    expect.verifySteps(["web_read_group"]);
    expect(badge).toHaveText("15");
    expect(secondBadge).toHaveText("1");

    // changing the stage resets the rotting
    await contains(`${rottingRecords}:eq(0)`).dragAndDrop(".o_kanban_group:eq(1)");
    expect(badge).toHaveText("14");
    expect(secondBadge).toHaveText("1");
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:eq(1) .o_kanban_record.oe_kanban_card_rotting").toHaveCount(1);
    // the source column is reloaded, which keeps the count up to date
    expect(`${column} .o_kanban_record`).toHaveCount(10);

    await clickKanbanLoadMore(0);
    expect(`${column} .o_kanban_record`).toHaveCount(16);
    expect(rottingRecords).toHaveCount(14);
    expect(badge).toHaveText("14");
    expect.verifySteps([]);
});
