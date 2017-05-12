odoo.define('web.list_keyboard_tests', function (require) {
"use strict";

var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [
                    {name: "Tyrion Lannister",},
                    {name: "Oliver Queen"},
                    {name: "Michael Scofield"},
                    {name: "Barry Allen"},
                    {name: "Bruce Wayne"},
                    {name: "Andrew Lincoln"},
                    {name: "Daenerys Targaryen",},
                    {name: "Joffrey Baratheon"},
                    {name: "Khal Drogo"},
                    {name: "Stannis Baratheon"},
                    {name: "Ramsay Bolton"},
                    {name: "Nightwing"},
                    {name: "Alfred Pennyworth",},
                    {name: "Bane"},
                    {name: "Selina"},
                    {name: "Vertigo"},
                    {name: "Victor"},
                    {name: "Luthor"},
                    {name: "Falcone",},
                    {name: "Jarvis"},
                    {name: "James Gordon"},
                    {name: "Maroni"},
                    {name: "Wade Wilson"},
                    {name: "Wade Wilson"},
                ]
            },
        };
    }
}, function () {

    QUnit.module('ListView Keyboard');

    QUnit.test('Listview selection', function (assert) {
        assert.expect(8);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
        });

        var $listview = list.$(".o_list_view");
        var shiftKeyPress = function (direction) {
            $listview.trigger($.Event("keydown", { which: direction, shiftKey: true }));
        };

        var controlKeyPress = function (direction) {
            $listview.trigger($.Event("keydown", { which: direction, ctrlKey: true }));
        };

        var $firstRecord = list.$el.find('.o_data_row').first();
        $firstRecord.find('input').trigger('click').focus();

        assert.ok($firstRecord.hasClass('o_row_selected'),'First record should be selected');

        // Press down key will select next record
        var $lastActiveRow = $firstRecord;
        $listview.trigger($.Event('keydown', {which: $.ui.keyCode.DOWN}));
        assert.ok(!$firstRecord.hasClass('o_row_selected'), 'First record should be unselected');
        assert.ok($lastActiveRow.next().hasClass('o_row_selected'), 'Second record should be selected');
        $lastActiveRow = $lastActiveRow.next();

        // On shift + down select currrent and next record
        shiftKeyPress(40);
        assert.ok($lastActiveRow.hasClass('o_row_selected') && $lastActiveRow.next().hasClass('o_row_selected'), "Selecting record with shift key should select multiple records");
        $lastActiveRow = $lastActiveRow.next();

        // On Ctrl + down will transfer focus to next record but don't select it
        controlKeyPress(40);
        assert.ok($($lastActiveRow.next()).hasClass('o_row_focused'), "Pressing down + control key should set focus on next row");

        // On Ctrl + up will transfer focus to previous record but don't select it
        controlKeyPress(38);
        assert.ok($lastActiveRow.hasClass('o_row_focused'), "Pressing up + control key should set focus on previous row");

        // On shift + up unselect previous record
        shiftKeyPress(38);
        assert.ok(!$($lastActiveRow.prev()).hasClass('o_row_selected'), "Pressing shift + up key should unselect previous row");
        $lastActiveRow = $lastActiveRow.prev();

        // On up(arrow) key it will select previous record
        $listview.trigger($.Event('keydown', { which: $.ui.keyCode.UP }));
        assert.ok($($lastActiveRow.prev()).hasClass('o_row_selected'), "First row should be selected");

        list.destroy();
    });

    QUnit.test('Editable Listview on escape discard the editable listview record', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="name"/></tree>',
        });

        list.$('tr.o_data_row:first td:not(.o_list_record_selector)').first().click();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE}));
        assert.strictEqual(list.renderer.currentRow, null, "Pressing escape in editable list view should discard the record");

        list.destroy();
    });

    QUnit.test('escape on listview create button should move user to previous view', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
            intercepts: {
                history_back: function () {
                    assert.step("move to previous view");
                },
            }
        });

        list.$buttons.find('.o_list_button_add').focus();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
        list.destroy();
    });
});

});
