/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import { start } from '@mail/../tests/helpers/test_utils';

import { Items as legacySystrayItems } from 'web.SystrayMenu';
import testUtils from 'web.test_utils';
import { registerCleanup } from '@web/../tests/helpers/cleanup';

QUnit.module('note', {}, function () {
QUnit.module("ActivityMenu");

QUnit.test('note activity menu widget: create note from activity menu', async function (assert) {
    assert.expect(15);

    legacySystrayItems.push(ActivityMenu);
    registerCleanup(() => legacySystrayItems.pop());

    await start();
    assert.containsOnce(document.body, '.o_mail_systray_item',
        'should contain an instance of widget');
    await testUtils.nextTick();
    assert.strictEqual(document.querySelector('.o_notification_counter').innerText, '0',
        "should not have any activity notification initially");

    // toggle quick create for note
    await testUtils.dom.click(document.querySelector('.dropdown-toggle[title="Activities"]'));
    assert.containsOnce(document.body, '.o_no_activity',
        "should not have any activity preview");
    assert.doesNotHaveClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu should have Add new note CTA');
    await testUtils.dom.click(document.querySelector('.o_note_show'));
    assert.hasClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu should hide CTA when entering a new note');
    assert.doesNotHaveClass(document.querySelector('.o_note'), 'd-none',
        'ActivityMenu should display input for new note');

    // creating quick note without date
    await testUtils.fields.editInput(document.querySelector("input.o_note_input"), "New Note");
    await testUtils.dom.click(document.querySelector(".o_note_save"));
    assert.strictEqual(document.querySelector('.o_notification_counter').innerText, '1',
        "should increment activity notification counter after creating a note");
    assert.containsOnce(document.body, '.o_mail_preview[data-res_model="note.note"]',
        "should have an activity preview that is a note");
    assert.strictEqual(document.querySelector('.o_activity_filter_button[data-filter="today"]').innerText.trim(),
        "1 Today",
        "should display one note for today");

    assert.doesNotHaveClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(document.querySelector('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');

    // creating quick note with date
    await testUtils.dom.click(document.querySelector('.o_note_show'));
    document.querySelector('input.o_note_input').value = "New Note";
    await testUtils.dom.click(document.querySelector(".o_note_save"));
    assert.strictEqual(document.querySelector('.o_notification_counter').innerText, '2',
        "should increment activity notification counter after creating a second note");
    assert.strictEqual(document.querySelector('.o_activity_filter_button[data-filter="today"]').innerText.trim(),
        "2 Today",
        "should display 2 notes for today");
    assert.doesNotHaveClass(document.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(document.querySelector('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');
});
});
