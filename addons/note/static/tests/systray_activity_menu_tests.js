/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import testUtils from 'web.test_utils';

QUnit.module('note', {}, function () {
QUnit.module("ActivityMenu");

QUnit.test('note activity menu widget: create note from activity menu', async function (assert) {
    assert.expect(15);

    const { click } = await start();
    assert.containsOnce(document.body, '.o_ActivityMenuView',
        'should contain an instance of widget');
    assert.containsNone(document.body, '.o_ActivityMenuView_counter',
        "should not have any activity notification initially");

    // toggle quick create for note
    await click('.dropdown-toggle[title="Activities"]');
    assert.containsOnce(document.body, '.o_ActivityMenuView_noActivity',
        "should not have any activity preview");
    assert.containsOnce(document.body, '.o_note_show',
        'ActivityMenu should have Add new note CTA');
    await click('.o_note_show');
    assert.containsNone(document.body, '.o_note_show',
        'ActivityMenu should hide CTA when entering a new note');
    assert.containsOnce(document.body, '.o_note',
        'ActivityMenu should display input for new note');

    // creating quick note without date
    await testUtils.fields.editInput(document.querySelector("input.o_note_input"), "New Note");
    await click('.o_note_save');
    assert.strictEqual(document.querySelector('.o_ActivityMenuView_counter').innerText, '1',
        "should increment activity notification counter after creating a note");
    assert.containsOnce(document.body, '.o_ActivityMenuView_activityGroup[data-res_model="note.note"]',
        "should have an activity preview that is a note");
    assert.strictEqual(document.querySelector('.o_ActivityMenuView_activityGroupFilterButton[data-filter="today"]').innerText.trim(),
        "1 Today",
        "should display one note for today");

    assert.doesNotHaveClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.containsNone(document.body, '.o_note',
        'ActivityMenu add note input should be hidden');

    // creating quick note with date
    await click('.o_note_show');
    document.querySelector('input.o_note_input').value = "New Note";
    await click(".o_note_save");
    assert.strictEqual(document.querySelector('.o_ActivityMenuView_counter').innerText, '2',
        "should increment activity notification counter after creating a second note");
    assert.strictEqual(document.querySelector('.o_ActivityMenuView_activityGroupFilterButton[data-filter="today"]').innerText.trim(),
        "2 Today",
        "should display 2 notes for today");
    assert.doesNotHaveClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.containsNone(document.body, '.o_note',
        'ActivityMenu add note input should be hidden');
});
});
