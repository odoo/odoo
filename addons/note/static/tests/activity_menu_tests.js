/** @odoo-module **/

import { click, start } from "@mail/../tests/helpers/test_utils";
import { getFixture, editInput, patchDate } from "@web/../tests/helpers/utils";

let target;

QUnit.module("note activity menu", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("create note from activity menu without date", async function (assert) {
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    assert.containsNone(target, ".o-mail-ActivityMenu-counter");
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(
        target,
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)"
    );
    assert.containsOnce(target, "button:contains(Add new note)");
    await click("button:contains(Add new note)");
    assert.containsNone(target, "button:contains(Add new note)");
    assert.containsOnce(target, ".o-mail-ActivityMenu-show");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New Note");
    await click("button:contains(SAVE)");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(1)");
    assert.containsOnce(target, ".o-mail-ActivityGroup");
    assert.containsOnce(target, ".o-mail-ActivityGroup:contains(note.note)");
    assert.containsOnce(target, "button:contains(1 Today)");
    assert.containsOnce(target, "button:contains(Add new note)");
    assert.containsNone(target, ".o-mail-ActivityMenu-show");
    assert.containsNone(target, ".o-mail-ActivityMenu-input");
    await click("button:contains(Add new note)");
    assert.containsNone(target, "button:contains(Add new note)");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New Note");
    await click("button:contains(SAVE)");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(2)");
    assert.containsOnce(target, "button:contains(2 Today)");
});

QUnit.test("create note from activity menu with date", async function (assert) {
    patchDate(2023, 1, 1, 6, 0, 0);
    const { DateTime } = luxon;
    const today = DateTime.utc();
    const futureDay = today.plus({ days: 2 });
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    assert.containsNone(target, ".o-mail-ActivityMenu-counter");

    await click(".o_menu_systray i[aria-label='Activities']");
    await click("button:contains(Add new note)");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New Note");
    await editInput(
        target,
        "input.o_datetime_input",
        futureDay.toString(luxon.DateTime.DATE_SHORT)
    );
    await click("button:contains(SAVE)");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(1)");
    assert.containsOnce(target, ".o-mail-ActivityGroup");
    assert.containsOnce(target, ".o-mail-ActivityGroup:contains(note.note)");
    assert.containsOnce(target, "button:contains(1 Future)");
});
