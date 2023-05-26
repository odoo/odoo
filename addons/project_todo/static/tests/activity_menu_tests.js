/** @odoo-module **/

import { click, start } from "@mail/../tests/helpers/test_utils";
import { getFixture, editInput, patchDate } from "@web/../tests/helpers/utils";

let target;

QUnit.module("todo activity menu", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("create todo from activity menu without date", async function (assert) {
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    assert.containsNone(target, ".o-mail-ActivityMenu-counter");
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(
        target,
        ".o-mail-ActivityMenu:contains(Congratulations, you're done with your activities.)"
    );
    assert.containsOnce(target, ".btn:contains(Add a To-do)");
    await click(".btn:contains(Add a To-do)");
    assert.containsNone(target, ".btn:contains(Add a To-do)");
    assert.containsOnce(target, ".o-mail-ActivityMenu-show");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New To-do");
    await click(".btn:contains(SAVE)");
    // Need to reopen systray as it automatically closes when a todo is created
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(1)");
    assert.containsOnce(target, ".o-mail-ActivityGroup");
    assert.containsOnce(target, ".o-mail-ActivityGroup:contains(project.task)");
    assert.containsOnce(target, ".btn:contains(1 Today)");
    assert.containsOnce(target, ".btn:contains(Add a To-do)");
    assert.containsNone(target, ".o-mail-ActivityMenu-show");
    assert.containsNone(target, ".o-mail-ActivityMenu-input");
    await click(".btn:contains(Add a To-do)");
    assert.containsNone(target, ".btn:contains(Add a To-do)");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New To-do");
    await click(".btn:contains(SAVE)");
    // Need to reopen systray as it automatically closes when a todo is created
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(2)");
    assert.containsOnce(target, ".btn:contains(2 Today)");
});

QUnit.test("create to-do from activity menu with date", async function (assert) {
    patchDate(2023, 1, 1, 6, 0, 0);
    const { DateTime } = luxon;
    const today = DateTime.utc();
    const futureDay = today.plus({ days: 2 });
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    assert.containsNone(target, ".o-mail-ActivityMenu-counter");

    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".btn:contains(Add a To-do)");
    await editInput(target, "input.o-mail-ActivityMenu-input", "New To-do");
    await editInput(
        target,
        "input.o_datetime_input",
        futureDay.toString(luxon.DateTime.DATE_SHORT)
    );
    await click(".btn:contains(SAVE)");
    // Need to reopen systray as it automatically closes when a todo is created
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Activities']");
    await click(".o_menu_systray i[aria-label='Activities']");
    assert.containsOnce(target, ".o-mail-ActivityMenu-counter:contains(1)");
    assert.containsOnce(target, ".o-mail-ActivityGroup");
    assert.containsOnce(target, ".o-mail-ActivityGroup:contains(project.task)");
    assert.containsOnce(target, ".btn:contains(1 Future)");
});
