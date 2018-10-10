odoo.define('mrp.tests', function (require) {
"use strict";

var field_registry = require('web.field_registry');
var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

QUnit.module('mrp', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    state: {
                        string: "State",
                        type: "selection",
                        selection: [['waiting', 'Waiting'], ['chilling', 'Chilling']],
                    },
                    duration: {string: "Duration", type: "float"},
                },
                records: [{
                    id: 1,
                    state: 'waiting',
                    duration: 6000,
                }],
                onchanges: {},
            },
        };
    },
}, function () {

    QUnit.test("pdf_viewer: upload rendering", function (assert) {
        assert.expect(6);

        testUtils.patch(field_registry.map.pdf_viewer, {
            on_file_change: function (ev) {
                ev.target = {files: [new Blob()]};
                this._super.apply(this, arguments);
            },
            _getURI: function (fileURI) {
                var res = this._super.apply(this, arguments);
                assert.step('_getURI');
                assert.ok(_.str.startsWith(fileURI, 'blob:'));
                this.PDFViewerApplication = {
                    open: function (URI) {
                        assert.step('open');
                        assert.ok(_.str.startsWith(URI, 'blob:'));
                    },
                };
                return 'about:blank';
            },
        });

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="document" widget="pdf_viewer"/>' +
                '</form>',
        });

        // first upload initialize iframe
        form.$('input[type="file"]').trigger('change');
        assert.verifySteps(['_getURI']);
        // second upload call pdfjs method inside iframe
        form.$('input[type="file"]').trigger('change');
        assert.verifySteps(['_getURI', 'open']);

        testUtils.unpatch(field_registry.map.pdf_viewer);
        form.destroy();
    });

    QUnit.test("bullet_state: basic rendering", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<field name="state" widget="bullet_state" options="{\'classes\': {\'waiting\': \'danger\'}}"/>' +
                '</form>',
        });

        assert.strictEqual(form.$('.o_field_widget').text(), "Waiting Materials",
            "the widget should be correctly named");
        assert.strictEqual(form.$('.o_field_widget .label-danger').length, 1,
            "the label should be danger");

        form.destroy();
    });

    QUnit.test("mrp_time_counter: basic rendering", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<field name="duration" widget="mrp_time_counter"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'mrp.workcenter.productivity') {
                    assert.ok(true, "the widget should fetch the mrp.workcenter.productivity");
                    return $.when([{
                        date_start: '2017-01-01 08:00:00',
                        date_end: '2017-01-01 10:00:00',
                    }, {
                        date_start: '2017-01-01 12:00:00',
                        date_end: '2017-01-01 12:30:00',
                    }]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name="duration"]').text(), "02:30:00",
            "the timer should be correctly set");

        form.destroy();
    });
});
});
