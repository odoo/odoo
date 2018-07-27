odoo.define('project.project_kanban_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('project', {
    beforeEach: function () {
        this.data = {
            'ir.attachment': {
                fields: {
                    name: {
                        string: "Name",
                        type: "char"
                    },
                },
                records: [{
                        id: 1,
                        name: "1.png"
                    },
                    {
                        id: 2,
                        name: "2.png"
                    },
                ]
            },
            'project.task': {
                fields: {
                    name: {
                        string: "Task Title",
                        type: "char"
                    },
                    sequence: {
                        string: "sequence",
                        type: "integer"
                    },
                    displayed_image_id: {
                        string: "cover",
                        type: "many2one",
                        relation: "ir.attachment"
                    },
                    kanban_state: {
                        string: "State",
                        type: "selection",
                        selection: [
                            ["abc", "ABC"],
                            ["def", "DEF"],
                            ["ghi", "GHI"]
                        ]
                    },
                },
                records: [{
                        id: 1,
                        name: "task1",
                        sequence: 1,
                        kanban_state: "abc"
                    },
                    {
                        id: 2,
                        name: "task2",
                        sequence: 2,
                        kanban_state: "abc"
                    },
                ]
            },
        };
    }
}, function () {
    QUnit.module('image test');

    QUnit.test('cover_image_test', function (assert) {
        assert.expect(6);
        var kanban = createView({
            View: KanbanView,
            model: 'project.task',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="name"/>' +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
                                        '<span class="fa fa-bars fa-lg"/>' +
                                    '</a>' +
                                    '<div class="dropdown-menu" role="menu">' +
                                        '<a type="set_cover" class="dropdown-item">Set Cover Image</a>'+
                                    '</div>' +
                                '</div>' +
                                '<div>'+
                                    '<field name="displayed_image_id" widget="attachment_image"/>'+
                                '</div>'+
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
            mockRPC: function(route, args) {
                if (args.model === 'ir.attachment' && args.method === 'search_read') {
                    return $.when([{
                        id: 1,
                        name: "1.png"
                    },{
                        id: 2,
                        name: "2.png"
                    }]);
                }
                if (args.model === 'project.task' && args.method === 'write') {
                    assert.step(args.args[0][0]);
                    return this._super(route, args);
                }
                return this._super(route, args);
            },
        });
        assert.strictEqual(kanban.$('img').length, 0, "Initially there is no image.");
        kanban.$('.o_dropdown_kanban [data-type=set_cover]').eq(0).click();
        // single click on image
        $('.modal').find("img[data-id='1']").click();
        $('.modal-footer .btn-primary').click();
        assert.strictEqual(kanban.$('img[data-src*="/web/image/1"]').length, 1, "Image inserted in record");
        $('.o_dropdown_kanban [data-type=set_cover]').eq(1).click();
        // double click on image
        $('.modal').find("img[data-id='2']").dblclick();
        assert.strictEqual(kanban.$('img[data-src*="/web/image/2"]').length, 1, "Image inserted after double click");
        // varify write on both kanban record
        assert.verifySteps([1,2]);
        kanban.destroy();
    });
});
});
