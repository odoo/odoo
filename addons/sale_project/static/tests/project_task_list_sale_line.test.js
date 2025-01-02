import { describe, expect, test } from "@odoo/hoot";
import { check, queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineProjectModels, projectModels } from "@project/../tests/project_models";

describe.current.tags("desktop");
defineProjectModels();

test("cannot edit sale_line_id when partners are different", async () => {
    mailModels.ResPartner._records = [
        { id: 101, name: "Deco Addict" },
        { id: 102, name: "Azure Interior" },
        ...mailModels.ResPartner._records,
    ];

    projectModels.ProjectTask._records = [
        { id: 1, partner_id: 101, sale_line_id: 1 },
        { id: 2, partner_id: 102, sale_line_id: 2 },
    ];

    projectModels.SaleOrderLine._records = [
        { id: 1, name: "order1" },
        { id: 2, name: "order2" },
    ];

    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `
            <list multi_edit="1" js_class="project_task_list">
                <field name="partner_id"/>
                <field name="sale_line_id"/>
            </list>
        `,
    });

    const [firstRow, secondRow] = queryAll(".o_data_row");

    await check(".o_list_record_selector input", { root: firstRow });
    await animationFrame();
    expect(queryOne("[name=sale_line_id]", { root: firstRow })).not.toHaveClass("o_readonly_modifier", {
        message: "None of the fields should be readonly",
    });
    expect(queryOne("[name=sale_line_id]", { root: secondRow })).not.toHaveClass("o_readonly_modifier", {
        message: "None of the fields should be readonly",
    });

    await check(".o_list_record_selector input", { root: secondRow });
    await animationFrame();
    expect(queryOne("[name=sale_line_id]", { root: firstRow })).toHaveClass("o_readonly_modifier", {
        message: "The sale_ine_id should be readonly",
    });
    expect(queryOne("[name=sale_line_id]", { root: secondRow })).toHaveClass("o_readonly_modifier", {
        message: "The sale_ine_id should be readonly",
    });
});
