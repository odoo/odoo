odoo.define('base_setup.res.config.form', function (require) {
    "use strict";

    const BaseSetting = require('base.settings');
    const QRCodeMixin = require('base_setup.QRCodeMixin');
    const viewRegistry = require('web.view_registry');

    const BaseSettingFormRenderer = BaseSetting.Renderer.extend({}, QRCodeMixin, {
        events: _.extend({}, QRCodeMixin.events, BaseSetting.Renderer.prototype.events),
    });

    const BaseSettingView = viewRegistry.get('base_settings');
    const BaseSettingConfigFormView = BaseSettingView.extend({
        config: _.extend({}, BaseSettingView.prototype.config, {
            Renderer : BaseSettingFormRenderer,
        }),
    });

    viewRegistry.add('base_settings', BaseSettingConfigFormView);

    return { BaseSettingFormRenderer, BaseSettingConfigFormView };

});
