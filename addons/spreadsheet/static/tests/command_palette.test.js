import { describe, expect, test } from "@odoo/hoot";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { animationFrame } from "@odoo/hoot-mock";
import { press } from "@odoo/hoot-dom";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { WebClient } from "@web/webclient/webclient";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

const serverData = /** @type {ServerData} */ ({});

describe.current.tags("desktop");
defineSpreadsheetModels();

test("Command palette is active on spreadsheet", async function () {
    await mountWithCleanup(WebClient);
    const { model } = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    await press(["control", "k"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
});

test("First item of command palette is insert link", async function () {
    await mountWithCleanup(WebClient);
    const { model } = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    await press(["control", "k"]);
    await animationFrame();
    expect(".o_command_name:first").toHaveText("Insert / Link");
});
