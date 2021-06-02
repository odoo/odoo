odoo.define('hr_skills.field_one_to_many_group_tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var testUtils = require('web.test_utils');

    var createView = testUtils.createView;

    QUnit.module('skills_widgets', {
        beforeEach: function () {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        line_ids: { string: "one2many field", type: "one2many", relation: 'line', relation_field: 'trululu' },
                        skill_ids: { string: "one2many field", type: "one2many", relation: 'partner_skill', relation_field: 'partner_id' },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        line_ids: [37, 38, 39],
                        skill_ids: [75, 76, 77]
                    }],
                    onchanges: {},
                },
                partner_skill: {
                    fields: {
                        skill_id: { string: "Name", type: "many2one", relation: 'skill'},
                        skill_type_id: { string: "Type", type: "many2one", relation: 'skill_type' },
                        skill_level_id: { string: "Level", type: "many2one", relation: 'skill_level' },
                        level_progress: { string: "Progress", type: "int" },
                    },
                    records: [{
                        id: 75,
                        skill_id: 444,
                        skill_type_id: 221,
                        skill_level_id: 112,
                        level_progress: 50,
                    }, {
                        id: 76,
                        skill_id: 445,
                        skill_type_id: 222,
                        skill_level_id:  111,
                        level_progress: 50,
                    }, {
                        id: 77,
                        skill_id: 446,
                        skill_type_id:  222,
                        skill_level_id:  111,
                        level_progress: 70,
                    }],
                },
                skill: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 444, name: 'Python' },
                        { id: 445, name: 'Piano' },
                        { id: 446, name: 'Flute' },
                    ]
                },
                skill_level: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 111, name: 'L1' },
                        { id: 112, name: 'Intermediate' }
                    ]
                },
                skill_type: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 221, name: 'Dev' },
                        { id: 222, name: 'Music' },
                    ]
                },
                line: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        line_type_id: { string: "Type", relation: 'line_type', type: "many2one" },
                        description: { string: "Description", type: "text" },
                        date_start: { string: "Date start", type: "date" },
                        date_end: { string: "Date end", type: "date" },
                        trululu: { string: "Trululu", type: "many2one", relation: 'partner' },
                        display_type: { string: "display type", type: "selection"},
                    },
                    records: [{
                        id: 37,
                        name: "ULB",
                        line_type_id: 50,
                        date_start: "2017-01-25",
                        date_end: "2019-01-25",
                        description: 'Hello',
                        trululu: 1,
                        display_type: 'classic',
                    }, {
                        id: 38,
                        name: "UCL",
                        line_type_id: 50,
                        date_start: "2013-01-25",
                        date_end: "2014-01-25",
                        description: 'World',
                        trululu: 1,
                        display_type: 'classic',
                    }, {
                        id: 39,
                        name: "KUL",
                        line_type_id: 51,
                        date_start: "2008-01-25",
                        description: 'Hi',
                        trululu: 1,
                        display_type: 'classic',
                    }],
                    onchanges: {},
                },
                line_type: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{
                        id: 50,
                        name: 'AAA',
                    }, {
                        id: 51,
                        name: 'BBB'
                    }],
                }
            };
        }
    }, function () {
        QUnit.test('resumé one2many field group by field render', async function (assert) {
            assert.expect(16);
            var form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="line_ids" widget="hr_resume">' +
                        '<tree>' +
                            '<field name="name"/>' +
                            '<field name="line_type_id"/>' +
                            '<field name="description"/>' +
                            '<field name="date_start"/>' +
                            '<field name="date_end"/>' +
                            '<field name="display_type"/>' +
                        '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });
            var $headers = form.$('.o_resume_group_header');
            assert.strictEqual($headers.length, 2, 'There should be 2 headers');
            assert.strictEqual($headers.find('td:contains(AAA)').length, 1, "it should have line type AAA");
            assert.strictEqual($headers.find('td:contains(BBB)').length, 1, "it should have line type BBB");

            var dataRows = form.$('.o_data_row');
            assert.strictEqual(dataRows.length, 3, 'There should be 3 data rows');

            var $row = $(dataRows[0]);
            assert.strictEqual($row.find('td:contains(01/25/2017)').length, 1, "it should have start date 01/25/2017");
            assert.strictEqual($row.find('td:contains(01/25/2019)').length, 1, "it should have end date 01/25/2019");
            assert.strictEqual($row.find('td:contains(ULB)').length, 1, "it should have line name ULB");
            assert.strictEqual($row.find('td:contains(Hello)').length, 1, "it should have line description Hello");

            $row = $(dataRows[1]);
            assert.strictEqual($row.find('td:contains(01/25/2013)').length, 1, "it should have start date 01/25/2013");
            assert.strictEqual($row.find('td:contains(01/25/2014)').length, 1, "it should have end date 01/25/2014");
            assert.strictEqual($row.find('td:contains(UCL)').length, 1, "it should have line name UCL");
            assert.strictEqual($row.find('td:contains(World)').length, 1, "it should have line description World");

            $row = $(dataRows[2]);
            assert.strictEqual($row.find('td:contains(01/25/2008)').length, 1, "it should have start date 01/25/2008");
            assert.strictEqual($row.find('td:contains(Current)').length, 1, "it should have end date Current");
            assert.strictEqual($row.find('td:contains(KUL)').length, 1, "it should have line name KUL");
            assert.strictEqual($row.find('td:contains(Hi)').length, 1, "it should have line description Hi");

            form.destroy();
        });
        QUnit.test('resumé one2many field group by field create', async function (assert) {
            assert.expect(5);
            var form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="line_ids" widget="hr_resume">' +
                        '<tree>' +
                            '<field name="name"/>' +
                            '<field name="line_type_id"/>' +
                            '<field name="description"/>' +
                            '<field name="date_start"/>' +
                            '<field name="date_end"/>' +
                        '</tree>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'line,false,form': '<form>' +
                            '<field name="name"/>' +
                            '<field name="line_type_id"/>' +
                            '<field name="description"/>' +
                            '<field name="date_start"/>' +
                            '<field name="date_end"/>' +
                        '</form>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'write') {
                        var new_line_data = args.args[1].line_ids[3][2];
                        assert.strictEqual(new_line_data.date_end, '2030-01-01');
                        assert.strictEqual(new_line_data.date_start, '2025-01-01');
                        assert.strictEqual(new_line_data.line_type_id, 50, "it should have the line type from context");
                        assert.strictEqual(new_line_data.name, 'new line');
                        assert.strictEqual(new_line_data.description, 'new description');
                    }
                    return result;
                },
            });

            await testUtils.form.clickEdit(form);
            await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a')[0]);

            // Fill line form (type should be set from the add button context)
            await testUtils.fields.editInput($('input[name="name"]'), 'new line');
            await testUtils.fields.editInput($('textarea[name="description"]'), 'new description');
            await testUtils.fields.editSelect($('input[name="date_start"]'), '2025-01-01');
            await testUtils.fields.editSelect($('input[name="date_end"]'), '2030-01-01');
            await testUtils.modal.clickButton('Save & Close');

            await testUtils.form.clickSave(form);
            form.destroy();
        });
        QUnit.test('resumé one2many field group by field delete', async function (assert) {
            assert.expect(2);
            var form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="line_ids" widget="hr_resume">' +
                        '<tree>' +
                            '<field name="name"/>' +
                            '<field name="line_type_id"/>' +
                            '<field name="description"/>' +
                            '<field name="date_start"/>' +
                            '<field name="date_end"/>' +
                        '</tree>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'line,false,form': '<form>' +
                            '<field name="name"/>' +
                            '<field name="line_type_id"/>' +
                            '<field name="description"/>' +
                            '<field name="date_start"/>' +
                            '<field name="date_end"/>' +
                        '</form>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'write') {
                        var orm_cmd = args.args[1].line_ids[2][0];
                        var id = args.args[1].line_ids[2][1];
                        assert.strictEqual(orm_cmd, 2, "it should delete resume line");
                        assert.strictEqual(id, 37, "it should delete resume line #37");
                    }
                    return result;
                },
            });

            await testUtils.form.clickEdit(form);
            await testUtils.dom.click(form.$('.o_list_record_remove')[0]);

            await testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('skills one2many field group by field render', async function (assert) {
            assert.expect(13);
            var form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="skill_ids" widget="hr_skills">' +
                        '<tree>' +
                            '<field name="skill_id"/>' +
                            '<field name="skill_type_id"/>' +
                            '<field name="skill_level_id"/>' +
                            '<field name="level_progress"/>' +
                        '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            var $headers = form.$('.o_group_header');
            assert.strictEqual($headers.length, 2, 'There should be 2 headers');
            assert.strictEqual($headers.find('td:contains(Dev)').length, 1, "it should have skill type Dev");
            assert.strictEqual($headers.find('td:contains(Music)').length, 1, "it should have skill type Music");

            var dataRows = form.$('.o_data_row');
            assert.strictEqual(dataRows.length, 3, 'There should be 3 data rows');

            var $row = $(dataRows[0]);
            assert.strictEqual($row.find('td:contains(Python)').length, 1, "it should have skill name Python");
            assert.strictEqual($row.find('td:contains(Intermediate)').length, 1, "it should have skill name Intermediate");
            assert.strictEqual($row.find('td:contains(50)').length, 1, "it should have skill progress 50");

            $row = $(dataRows[1]);
            assert.strictEqual($row.find('td:contains(Piano)').length, 1, "it should have skill name Piano");
            assert.strictEqual($row.find('td:contains(L1)').length, 1, "it should have skill level L1");
            assert.strictEqual($row.find('td:contains(50)').length, 1, "it should have skill progress 50");

            $row = $(dataRows[2]);
            assert.strictEqual($row.find('td:contains(Flute)').length, 1, "it should have skill name Flute");
            assert.strictEqual($row.find('td:contains(L1)').length, 1, "it should have skill level L1");
            assert.strictEqual($row.find('td:contains(70)').length, 1, "it should have skill progress 70");

            form.destroy();
        });
    });
});
