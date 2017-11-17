odoo.define('document.tests', function (require) {
    "use strict";

    var testUtils = require('web.test_utils');
    var FormView = require('web.FormView');

    var createView = testUtils.createView;

    QUnit.module('DocumentTest', {
        beforeEach: function () {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" }
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                    }]
                },
                'ir.attachment': {
                    fields: {
                        type: { string: "Type", type: "char" },
                        name: {string: "Name", type: "char"},
                        res_id: {string: "ResId", type: "integer"},
                        res_model: {string: "ResModel", type: "char"}
                    },
                    records: [{
                        id: 1,
                        type:"binary",
                        name: "attachment1",
                        res_id: 1,
                        res_model: 'partner'
                    },{
                        id: 2,
                        type:"binary",
                        name: "attachment2",
                        res_id: 1,
                        res_model: 'partner'
                    }]
                }
            };
        }
    }, function () {
        QUnit.module('DocView');
        QUnit.test('documentAttachmentTest', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="display_name"/>' +
                        '</sheet>' +
                    '</form>',
                res_id: 1,
                viewOptions: {hasSidebar: true},
                mockRPC: function (route, args) {
                    if (args.method === 'search_read' && args.model === 'ir.attachment') {
                        return $.when(this.data['ir.attachment'].records);
                    }
                    if (route === '/web/dataset/call_kw/ir.attachment/unlink') {
                        assert.strictEqual(args.args[0], 1, "Should have correct id of the attachment to be deleted");
                    }
                    return this._super.apply(this, arguments);
                }
            });

            assert.strictEqual(form.sidebar.$('.o_sidebar_delete_attachment').length, 2, "there should be two attachments");
            form.sidebar.$('.o_sidebar_delete_attachment:eq(0)').click();
            $('.modal-footer .btn-primary').click();
            assert.strictEqual(form.sidebar.$('.o_sidebar_delete_attachment').length, 1, "there should be only one attachment");
            form.destroy();
        });
    });
});
