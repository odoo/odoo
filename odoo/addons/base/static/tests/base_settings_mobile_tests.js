odoo.define('base.settings_mobile_tests', function (require) {
"use strict";

var BaseSetting = require('base.settings');

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var BaseSettingsView = view_registry.get('base_settings');
var createView = testUtils.createView;

// prevent the renderer from doing RPCs to fetch app icons
BaseSetting.Renderer.include({
    _getAppIconUrl: function () {
        return '';
    },
});

QUnit.module('mobile_base_settings_tests', {
    beforeEach: function () {
        this.data = {
            project: {
                fields: {
                    foo: {string: 'Foo', type: 'boolean'},
                    bar: {string: 'Bar', type: 'boolean'},
                },
            },
        };
    }
}, function () {

    QUnit.module('BaseSettings Mobile');

    QUnit.test('swipe settings in mobile', function (assert) {
        assert.expect(2);

        // mimic touchSwipe library's swipe method
        var oldSwipe = $.fn.swipe;
        var swipeLeft, swipeRight;
        $.fn.swipe = function (params) {
            swipeLeft = params.swipeLeft;
            swipeRight = params.swipeRight;
        };

        var form = createView({
            View: BaseSettingsView,
            model: 'project',
            data: this.data,
            arch: '<form string="Settings" class="oe_form_configuration o_base_settings">' +
                    '<div class="o_setting_container">' +
                        '<div class="settings_tab"/>'+
                        '<div class="settings">' +
                            '<div class="app_settings_block" data-string="CRM" data-key="crm">' +
                                '<div class="row mt16 o_settings_container">'+
                                    '<div class="col-12 col-lg-6 o_setting_box">'+
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
                                '</div>' +
                            '</div>' +
                            '<div class="app_settings_block" data-string="Project" data-key="project">' +
                                '<div class="row mt16 o_settings_container">'+
                                    '<div class="col-12 col-lg-6 o_setting_box">'+
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

        swipeLeft();
        assert.strictEqual(form.$('.settings .current').data('key'), 'project', 'current setting should be project');

        swipeRight();
        assert.strictEqual(form.$('.settings .current').data('key'), 'crm', 'current setting should be crm');

        $.fn.swipe = oldSwipe;
        form.destroy();
    });
});

});
