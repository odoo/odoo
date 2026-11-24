import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { download } from "@web/core/network/download";
import { defineHrHolidaysModels } from "./hr_holidays_test_helpers";

describe.current.tags("desktop");

class HrLeaveAllocation extends models.Model {
    _name = "hr.leave.allocation";

    name = fields.Char();

    _records = [{ id: 1, name: "Allocation" }];
}

defineHrHolidaysModels();
defineModels([HrLeaveAllocation]);

async function exportAll() {
    await contains(".o_cp_action_menus .dropdown-toggle").click();
    await contains(".o-dropdown--menu .o_export_all_menu").click();
}

function patchDownload() {
    patchWithCleanup(download, {
        _download: (options) => {
            const data = JSON.parse(options.data.data);
            expect.step({
                model: data.model,
                fields: data.fields.map((field) => [field.name, field.label]),
            });
        },
    });
}

onRpc("has_group", () => true);

test("Export All on the time off list downloads one re-importable file", async () => {
    patchDownload();
    await mountView({
        type: "list",
        resModel: "hr.leave",
        arch: `<list js_class="hr_holidays_payslip_list"><field name="employee_id"/></list>`,
        loadActionMenus: true,
    });
    await exportAll();
    // "External ID" is the label the import auto-maps to the id field
    expect.verifySteps([
        {
            model: "hr.leave",
            fields: [
                ["id", "External ID"],
                ["employee_id", "Employee"],
                ["work_entry_type_id/id", "Time Type/External ID"],
                ["request_date_from", "Request Start Date"],
                ["request_date_to", "Request End Date"],
            ],
        },
    ]);
});

test("Export All on the allocation list keeps the generic export", async () => {
    patchDownload();
    await mountView({
        type: "list",
        resModel: "hr.leave.allocation",
        arch: `<list js_class="hr_holidays_payslip_list"><field name="name"/></list>`,
        loadActionMenus: true,
    });
    await exportAll();
    expect.verifySteps([{ model: "hr.leave.allocation", fields: [["name", "Name"]] }]);
});
