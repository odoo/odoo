import { expect, test } from "@odoo/hoot";
import { queryText } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { TimezoneMismatchField } from "@web/views/fields/timezone_mismatch/timezone_mismatch_field";

class Localization extends models.Model {
    country = fields.Selection({
        selection: [
            ["belgium", "Belgium"],
            ["usa", "United States"],
        ],
        onChange: (record) => {
            record.tz_offset = "+4800";
        },
    });
    tz_offset = fields.Char();
    _records = [{ id: 1, country: "belgium" }];
}

defineModels([Localization]);

test("in a list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "localization",
        resId: 1,
        arch: /*xml*/ `
            <list string="Localizations" editable="top">
                <field name="tz_offset" column_invisible="True"/>
                <field name="country" widget="timezone_mismatch" />
            </list>
        `,
    });
    expect("td:contains(Belgium)").toHaveCount(1);
    await contains(".o_data_cell").click();
    expect(".o_field_widget[name=country] select").toHaveCount(1);
    await contains(".o_field_widget[name=country] select").select(`"usa"`);
    expect(".o_data_cell:first").toHaveText(
        /United States\s+\([0-9]+\/[0-9]+\/[0-9]+ [0-9]+:[0-9]+:[0-9]+\)/
    );
    expect(".o_tz_warning").toHaveCount(1);
});

test("in a form view", async () => {
    await mountView({
        type: "form",
        resModel: "localization",
        resId: 1,
        arch: /*xml*/ `
            <form>
                <field name="tz_offset" invisible="True"/>
                <field name="country" widget="timezone_mismatch" />
            </form>
        `,
    });
    expect(`.o_field_widget[name="country"]:contains(Belgium)`).toHaveCount(1);
    expect(".o_field_widget[name=country] select").toHaveCount(1);
    await contains(".o_field_widget[name=country] select").select(`"usa"`);
    expect(queryText(`.o_field_widget[name="country"]:first`)).toMatch(
        /United States\s+\([0-9]+\/[0-9]+\/[0-9]+ [0-9]+:[0-9]+:[0-9]+\)/
    );
    expect(".o_tz_warning").toHaveCount(1);
});

test("timezone_mismatch_field mismatch property", () => {
    const testCases = [
        {userOffset: "-1030", browserOffset: 630, expectedMismatch: false},
        {userOffset: "+0000", browserOffset: 0, expectedMismatch: false},
        {userOffset: "+0345", browserOffset: -225, expectedMismatch: false},
        {userOffset: "+0500", browserOffset: -300, expectedMismatch: false},
        {userOffset: "+0200", browserOffset: 120, expectedMismatch: true},
        {userOffset: "+1200", browserOffset: 0, expectedMismatch: true},
    ];

    for (const testCase of testCases) {
        patchWithCleanup(Date.prototype, {
            getTimezoneOffset: () => testCase.browserOffset,
        });

        patchWithCleanup(TimezoneMismatchField.prototype, {
            props: {
                name: "tz",
                tzOffsetField: "tz_offset",
                record: {
                    data: {
                        tz: "Test/Test",
                        tz_offset: testCase.userOffset,
                    },
                },
            },
        });

        const mockField = Object.create(TimezoneMismatchField.prototype);

        expect(mockField.mismatch).toBe(testCase.expectedMismatch);
    }
});
