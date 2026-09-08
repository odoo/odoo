import { describe, expect, test } from "@odoo/hoot";
import { press, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

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

test("a command that has a keyboard shortcut shows it", async function () {
    await mountWithCleanup(WebClient);
    const { model } = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    await press(["control", "k"]);
    await animationFrame();
    // `confirm: false`: confirming would run the selected command and close
    // the palette.
    await contains(".o_command_palette_search input").edit("Copy", { confirm: false });
    await animationFrame();
    // `toInclude`, not `toEqual`: web's own hotkey commands fuzzy-match too.
    expect(queryAllTexts(".o_command_hotkey")).toInclude("Edit / Copy\nCONTROL + C");
});
