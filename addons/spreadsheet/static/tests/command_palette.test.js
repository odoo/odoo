import { describe, expect, test } from "@odoo/hoot";
import { createModelAndMountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { animationFrame } from "@odoo/hoot-mock";
import { press } from "@odoo/hoot-dom";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { WebClient } from "@web/webclient/webclient";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetModels();

test("Command palette is active on spreadsheet", async function () {
    await mountWithCleanup(WebClient);
    await createModelAndMountSpreadsheet();
    await press(["control", "k"]);
    await animationFrame();
    expect(".o_command_palette").toHaveCount(1);
});

test("First item of command palette is Print", async function () {
    await mountWithCleanup(WebClient);
    await createModelAndMountSpreadsheet();
    await press(["control", "k"]);
    await animationFrame();
    expect(".o_command_name:first").toHaveText("File / Print");
});

test("First item with a shortcut is Edit / Copy and the shortcut is displayed", async function () {
    await mountWithCleanup(WebClient);
    await createModelAndMountSpreadsheet();
    await press(["control", "k"]);
    await animationFrame();
    expect(".o_command_hotkey:first").toHaveText("Edit / Copy\nCONTROL + C");
});

test("non-readonly items are not visible on a readonly spreadsheet", async () => {
    await mountWithCleanup(WebClient);
    const { model } = await createModelAndMountSpreadsheet();
    await press(["control", "k"]);
    await animationFrame();
    await contains(".o_command_palette_search input").edit("insert");
    await animationFrame();
    expect("#o_command_empty").toHaveCount(0);
    await press(["escape"]);
    model.updateMode("readonly");
    await animationFrame();
    await press(["control", "k"]);
    await animationFrame();
    await contains(".o_command_palette_search input").edit("insert");
    await animationFrame();
    expect("#o_command_empty").toHaveCount(1);
});
