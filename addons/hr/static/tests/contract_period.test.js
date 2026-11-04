import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { makeMockServer, mountView } from "@web/../tests/web_test_helpers";

import { defineHrModels } from "@hr/../tests/hr_test_helpers";

defineHrModels();

test("contract period shows the ongoing, else next, else last contract", async () => {
    mockDate("2026-11-03 10:00:00");
    const { env } = await makeMockServer();
    const createEmployee = (name, contracts) => {
        const employeeId = env["hr.employee"].create({ name });
        for (const [start, end] of contracts) {
            env["hr.version"].create({
                employee_id: employeeId,
                date_version: start || "2026-01-01",
                contract_date_start: start,
                contract_date_end: end,
            });
        }
    };
    createEmployee("Next contract, nothing ongoing", [
        ["2026-11-02", "2026-11-02"],
        ["2026-11-04", "2026-11-04"],
        ["2026-11-05", "2026-11-05"],
        ["2026-11-16", "2026-11-30"],
    ]);
    createEmployee("Ongoing with future contracts", [
        ["2026-11-02", "2026-11-02"],
        ["2026-11-03", "2026-11-03"],
        ["2026-11-04", "2026-11-04"],
        ["2026-11-16", "2026-11-30"],
    ]);
    createEmployee("Ongoing open-ended after renewals", [
        ["2026-01-01", "2026-01-31"],
        ["2026-02-01", "2026-02-28"],
        ["2026-03-01", false],
    ]);
    createEmployee("Ongoing, last day", [["2026-10-01", "2026-11-03"]]);
    createEmployee("Last contract, ended", [
        ["2026-01-01", "2026-06-30"],
        ["2026-07-01", "2026-10-31"],
    ]);
    createEmployee("No contract", [[false, false]]);

    await mountView({
        type: "kanban",
        resModel: "hr.employee",
        arch: `
            <kanban default_order="id">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <field name="version_ids" widget="contract_period"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_record .o_field_widget[name=version_ids]")).toEqual([
        "Nov 4 - Nov 4",
        "Nov 3 - Nov 3",
        "Mar 1",
        "Oct 1 - Nov 3",
        "Jul 1 - Oct 31",
        "",
    ]);
    expect(queryAllTexts(".o_field_widget[name=version_ids] .text-danger")).toEqual([
        "Jul 1 - Oct 31",
    ]);
});
