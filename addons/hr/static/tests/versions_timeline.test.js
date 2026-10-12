import { expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { makeMockServer, mountView } from "@web/../tests/web_test_helpers";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

defineHrModels();

async function assertVersionOrderOnCreate(initialDates, newDate, expectedOrder, message) {
    const { env } = await makeMockServer();
    const employeeId = env["hr.employee"].create({ name: "Employee" });

    const versionIds = initialDates.map((date) =>
        env["hr.version"].create({
            date_version: date,
            display_name: luxon.DateTime.fromISO(date).toFormat("MMM dd, yyyy"),
            employee_id: employeeId,
        })
    );
    env["hr.employee"].write([employeeId], { version_id: versionIds[1] });

    const VersionsTimeline = registry.category("fields").get("versions_timeline").component;

    // Capture the record object for triggering the load method
    let testRecord = null;
    patch(VersionsTimeline.prototype, {
        setup() {
            super.setup(...arguments);
            testRecord = this.props.record;
        }
    });

    await mountView({
        type: "form",
        resModel: "hr.employee",
        resId: employeeId,
        arch: `
            <form>
                <header>
                    <field name="version_id" widget="versions_timeline" />
                </header>
            </form>`,
    });

    // Assert the initial order of versions is as expected
    expect(queryAllTexts(".o_arrow_button_wrap .o_arrow_button")).toEqual(
        ["May 01, 2024", "Mar 01, 2024", "Jan 01, 2024"],
        { message }
    );

    const newVersionId = env["hr.version"].create({
        date_version: newDate,
        display_name: luxon.DateTime.fromISO(newDate).toFormat("MMM dd, yyyy"),
        employee_id: employeeId,
    });

    // Load the new version into the record's model context and wait for re-render
    await testRecord.model.load({
        context: {
            ...testRecord.model.env.searchModel.context,
            version_id: newVersionId,
        },
    });
    const expectedLabel = luxon.DateTime.fromISO(newDate).toFormat("MMM dd, yyyy");
    await waitFor(`.o_arrow_button_wrap .o_arrow_button:contains('${expectedLabel}')`);

    // Assert the DOM is in the correct order after the new version is added
    expect(queryAllTexts(".o_arrow_button_wrap .o_arrow_button")).toEqual(expectedOrder, { message });
}

// Note: The DOM elements are ordered descendingly (newest first).
// The UI only looks ascending because CSS row-reverse flips them in StatusBarField widget.

test("Loading a new future version sorts it correctly", async () => {
    await assertVersionOrderOnCreate(
        ["2024-01-01", "2024-03-01", "2024-05-01"],
        "2024-06-01",
        ["Jun 01, 2024", "May 01, 2024", "Mar 01, 2024", "Jan 01, 2024"],
        "new future version should appear first in the descending DOM order"
    );
});

test("Loading a new middle version sorts it correctly", async () => {
    await assertVersionOrderOnCreate(
        ["2024-01-01", "2024-03-01", "2024-05-01"],
        "2024-04-01",
        ["May 01, 2024", "Apr 01, 2024", "Mar 01, 2024", "Jan 01, 2024"],
        "new middle version should be inserted chronologically between the nearest versions"
    );
});

test("Loading a new older version sorts it correctly", async () => {
    await assertVersionOrderOnCreate(
        ["2024-01-01", "2024-03-01", "2024-05-01"],
        "2023-12-01",
        ["May 01, 2024", "Mar 01, 2024", "Jan 01, 2024", "Dec 01, 2023"],
        "new older version should appear last in the descending DOM order"
    );
});
