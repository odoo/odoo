odoo.define('web.base_setting_test', function (require) {
"use strict";

var BaseSetting = require('base.settings');

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;
var BaseSettingsView = view_registry.get('base_settings');

BaseSetting.Renderer.include({
    _getAppIconUrl: function() {
        return "#test:";
    }
});

QUnit.module('base_settings_tests', {
    beforeEach: function () {
        this.data = {
            project: {
                fields: {
                    foo: {string: "Foo", type: "boolean"},
                    bar: {string: "Bar", type: "boolean"},
                },
            },
        };
    }
}, function () {

    QUnit.module('BaseSetting');

    QUnit.test('change setting on nav bar click in base settings', function (assert) {
        assert.expect(4);

        var form = createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<div class="o_panel">' +
                        '<div class="setting_search">' +
                            '<input type="text" class="searchInput" placeholder="Search..."/>' +
                        '</div> ' +
                    '</div> ' +
                    '<header>' +
                        '<button string="Save" type="object" name="execute" class="oe_highlight" />' +
                        '<button string="Cancel" type="object" name="cancel" class="oe_link" />' +
                    '</header>' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>'+
                        '<div class="settings">' +
                            '<div class="notFound o_hidden">No Record Found</div>' +
                            '<div class="app_settings_block" string="CRM" data-key="crm">' +
                                '<div class="row mt16 o_settings_container">'+
                                    '<div class="col-xs-12 col-md-6 o_setting_box">'+
                                        '<div class="o_setting_left_pane">' +
                                            '<field name="bar"/>'+
                                        '</div>'+
                                        '<div class="o_setting_right_pane">'+
                                            '<label for="bar"/>'+
                                            '<div class="text-muted">'+
                                                'this is bar'+
                                            '</div>'+
                                        '</div>' +
                                    '</div>'+
                                    '<div class="col-xs-12 col-md-6 o_setting_box">'+
                                        '<div class="o_setting_left_pane">' +
                                            '<field name="foo"/>'+
                                        '</div>'+
                                        '<div class="o_setting_right_pane">'+
                                            '<label for="foo"/>'+
                                            '<div class="text-muted">'+
                                                'this is foo'+
                                            '</div>'+
                                        '</div>' +
                                    '</div>'+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</form>',
        });

        form.$("div[setting='project']").click();
        assert.strictEqual(form.$('.selected').attr('data-key'),"crm","crm setting selected");
        assert.strictEqual(form.$(".settings .app_settings_block").hasClass('o_hidden'),false,"project settings show");
        form.$('.searchInput').val('b').trigger('keyup');
        assert.strictEqual($('.highlighter').html(),"B","b word hilited");
        form.$('.searchInput').val('bx').trigger('keyup');
        assert.strictEqual(form.$('.notFound').hasClass('o_hidden'),false,"record not found message shown");
        form.destroy();
    });
});
});