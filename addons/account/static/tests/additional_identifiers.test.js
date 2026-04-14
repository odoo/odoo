import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";


class Partner extends models.Model {
    _records = [
        {
            id: 1,
            country_code: "FR",
            additional_identifiers: { FR_SIRET: "73282932000074" },
        },
        {
            id: 2,
            country_code: "FR",
            additional_identifiers: {},
        },
    ];

    additional_identifiers = fields.Json({ string: "Additional identifiers" });
    country_code = fields.Char({ string: "Country Code" });

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <field name="country_code" invisible="1"/>
                    <field name="additional_identifiers" widget="additional_identifiers_button" nolabel="1"/>
                    <field name="additional_identifiers" widget="additional_identifiers_list" nolabel="1"/>
                </sheet>
            </form>
        `,
    };
}

defineModels([Partner]);
defineMailModels();

/** Default mock for the metadata RPC — a minimal FR-focused metadata dict. */
function mockMetadata() {
    onRpc(
        "res.partner",
        "get_available_additional_identifiers_metadata",
        () => ({
            FR_SIRET: {
                label: "France SIRET",
                sequence: 10,
                placeholder: "73282932000074",
            },
            FR_SIREN: {
                label: "France SIREN",
                sequence: 20,
                placeholder: "732829320",
            },
            EAN_GLN: {
                label: "EAN/GLN",
                sequence: 100,
                placeholder: "9780471117094",
                help: "Global Location Number",
            },
        }),
    );
}

test.tags("desktop");
test("list widget renders existing identifiers as labeled inputs", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
    });

    // The list is rendered with the stored identifier
    expect(".o_additional_identifiers_list").toHaveCount(1);
    expect(".o_additional_identifiers_list label").toHaveCount(1);
    expect(".o_additional_identifiers_list label").toHaveText("France SIRET");
    expect(".o_additional_identifiers_list input").toHaveCount(1);
    expect(".o_additional_identifiers_list input").toHaveValue("73282932000074");
});

test.tags("desktop");
test("list widget hides when there are no identifiers", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
    });

    // Empty identifiers => list should not render any input row
    expect(".o_additional_identifiers_list").toHaveCount(0);
});

test.tags("desktop");
test("button widget dropdown lists only identifiers not yet in use", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
    });

    // Open the dropdown
    await contains(".dropdown-toggle").click();

    // FR_SIRET is already used, so it should be excluded
    const labels = queryAllTexts(".o-dropdown--menu .o-dropdown-item");
    expect(labels).toEqual(["France SIREN", "EAN/GLN"]);
});

test.tags("desktop");
test("adding an identifier via the dropdown appends a row with an empty input", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
    });

    await contains(".dropdown-toggle").click();
    await contains(".o-dropdown--menu .o-dropdown-item:contains('France SIREN')").click();
    await advanceTime(100); // flush debouncedCommitChanges (50ms)
    await animationFrame();

    // Two inputs now (existing SIRET + new empty SIREN)
    expect(".o_additional_identifiers_list input").toHaveCount(2);

    const labels = queryAllTexts(".o_additional_identifiers_list label");
    expect(labels).toEqual(["France SIRET", "France SIREN"]);

    const values = queryAll(".o_additional_identifiers_list input").map((i) => i.value);
    expect(values).toEqual(["73282932000074", ""]);
});

test.tags("desktop");
test("editing an input commits the value back to the record", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
    });

    // Add a SIREN entry
    await contains(".dropdown-toggle").click();
    await contains(".o-dropdown--menu .o-dropdown-item:contains('France SIREN')").click();

    // Type a value
    await contains(".o_additional_identifiers_list input").edit("732829320");

    expect(".o_additional_identifiers_list input").toHaveValue("732829320");
});

test.tags("desktop");
test("clearing an input removes the identifier from the list", async () => {
    mockMetadata();

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
    });

    // Clear the existing value
    await contains(".o_additional_identifiers_list input").edit("");

    // The row is removed (empty identifiers dict => list hidden)
    expect(".o_additional_identifiers_list").toHaveCount(0);
});

test.tags("desktop");
test("dropdown respects identifier sequence ordering", async () => {
    onRpc(
        "res.partner",
        "get_available_additional_identifiers_metadata",
        () => ({
            EAN_GLN: { label: "EAN/GLN", sequence: 100 },
            FR_SIRET: { label: "France SIRET", sequence: 10 },
            FR_SIREN: { label: "France SIREN", sequence: 20 },
        })
    );

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
    });

    await contains(".dropdown-toggle").click();

    // Ordered by sequence: FR_SIRET (10), FR_SIREN (20), EAN_GLN (100)
    expect(queryAllTexts(".o-dropdown--menu .o-dropdown-item")).toEqual([
        "France SIRET",
        "France SIREN",
        "EAN/GLN",
    ]);
});

test.tags("desktop");
test("dropdown is hidden when no identifier types are available", async () => {
    onRpc(
        "res.partner",
        "get_available_additional_identifiers_metadata",
        () => ({
            FR_SIRET: { label: "France SIRET", sequence: 10 },
        }),
    );

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1, // already has FR_SIRET → no remaining options
    });

    // The Dropdown component is rendered conditionally (t-if on length > 0)
    expect(".dropdown-toggle").toHaveCount(0);
});
