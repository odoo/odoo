odoo.define('mail.document_viewer', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('mail', {}, function () {

QUnit.module('Document Viewer', {
    beforeEach: function () {
        this.data = {
            attachments: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    image: {string: "Image", type: "binary"},
                    mimetype: {string: "mimetype", type: "char"},
                },
                records: [
                    {id: 1, foo: "yop", 'image': 'R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==', mimetype: 'image'},
                    {id: 2, foo: "blip", mimetype: 'video'},
                    {id: 3, foo: "gnap", mimetype: 'application/pdf'},
                    {id: 4, foo: "blip", mimetype: 'image'},
                    {id: 5, foo: "flip", mimetype: 'application/msword'},
                ]
            },
        };
    },
});

QUnit.test('test document viewer in kanban view', function (assert) {
    assert.expect(4);

    var kanban = createView({
        View: KanbanView,
        model: 'attachments',
        data: this.data,
        arch: '<kanban class="o_kanban_test">' +
                  '<field name="id"/>' +
                  '<field name="mimetype"/>' +
                  '<templates><t t-name="kanban-box"><div class="oe_kanban_global_click">' +
                    '<t t-name="AttachmentView">' +
                        '<t t-set="has_doc_preview" t-value="record.mimetype.value == \'image\' or record.mimetype.value == \'video\' or record.mimetype.value == \'application/pdf\'"/>' +
                        '<div t-attf-class="o_attachment_view #{has_doc_preview ? \'o_document_preview\' : \'\'}">' +
                            '<t t-set="type" t-value="record.mimetype.value.split(\'/\').shift()"/>' +
                            '<img t-if="type == \'image\'" class="img img-responsive o_attachment_image" t-attf-src="/web/image/#{record.id.raw_value}" />' +
                            '<i t-if="type != \'image\'" class="o_image" t-att-data-mimetype="record.mimetype.value"/>' +
                            '<div t-attf-class="o_attachment_preview #{type == \'image\' ? \'o_image_overlay\' : \'\'}" t-attf-title="record.name.raw_value">' +
                                '<a t-if="type != \'image\' and type != \'video\' and record.mimetype.value != \'application/pdf\'" t-attf-href="/web/content/#{record.id.raw_value}?download=1" class="o_overlay_download"/>' +
                                '<a t-attf-href="/web/content/#{record.id.raw_value}?download=1" class="o_download_content pull-right" t-attf-title="Download this #{type == \'image\' ? \'image\' : type == \'video\' ? \'video\' : \'document\'}">' +
                                    '<i t-attf-class="fa fa-download #{type == \'image\' ? \'text-white\' : \'text-black\'}" aria-hidden="true" />' +
                                '</a>' +
                            '</div>' +
                        '</div>' +
                    '</t>' +
                  '</div></t></templates>' +
              '</kanban>',
        intercepts: {
            attachmentsPreview: function (event) {
                assert.step(event.target.recordData.mimetype)
            },
        }
    });

    kanban.$('.o_kanban_record:nth-child(1) .o_attachment_preview').click();
    $('.o_close_btn').click();
    kanban.$('.o_kanban_record:nth-child(2) .o_attachment_preview').click();
    $('.o_close_btn').click();
    kanban.$('.o_kanban_record:nth-child(3) .o_attachment_preview').click();
    $('.o_close_btn').click();
    assert.verifySteps(['image', 'video', 'application/pdf'])
    kanban.destroy();
});

});

});