odoo.define('web.form_benchmarks', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Form View', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    many2many: { string: "bar", type: "many2many", relation: 'bar'},
                },
                records: [
                    { id: 1, many2many: []},
                ],
                onchanges: {}
            },
            bar: {
                fields: {
                    char: {string: "char", type: "char"},
                    many2many: { string: "pokemon", type: "many2many", relation: 'pokemon'},
                },
                records: [],
                onchanges: {}
            },
            pokemon: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [],
                onchanges: {}
            },
        };
        this.arch = null;
        this.run = function (assert, done, cb) {
            var data = this.data;
            var arch = this.arch;
            new Benchmark.Suite({})
                .add('form', function () {
                    var list = createView({
                        View: FormView,
                        model: 'foo',
                        data: data,
                        arch: arch,
                        res_id: 1,
                    });
                    if (cb) {
                        cb(list);
                    }
                    list.destroy();
                })
                .on('cycle', function(event) {
                    assert.ok(true, String(event.target));
                })
                .on('complete', done)
                .run({ 'async': true });
        };
    }
}, function () {
    QUnit.test('x2many with 250 rows, 2 fields (with many2many_tags, and modifiers), onchanges, and edition', function (assert) {
        var done = assert.async();
        assert.expect(1);

        this.data.foo.onchanges.many2many = function (obj) {
            obj.many2many = [5].concat(obj.many2many);
        };
        for (var i = 2; i < 500; i) {
            this.data.bar.records.push({
                id: i,
                char: "automated data",
            });
            this.data.foo.records[0].many2many.push(i);
        }
        this.arch =
                '<form string="Partners">' +
                    '<field name="many2many">' +
                        '<tree editable="top" limit="250">' +
                            '<field name="char"/>' +
                            '<field name="many2many" widget="many2many_tags" attrs="{\'readonly\': [(\'char\', \'==\', \'toto\')]}"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>';
        this.run(assert, done, function (form) {
            testUtils.form.clickEdit(form);
            form.$('.o_data_cell:first').click();
            form.$('input:first').val("tralala").trigger('input');
        });
    });
});

});