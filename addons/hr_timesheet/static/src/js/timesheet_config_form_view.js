odoo.define('hr_timesheet.res.config.form', function (require) {
    "use strict";

    const viewRegistry = require('web.view_registry');
    const BaseSetting = require('base.settings');
    const QRCodeMixin = require('base_setup.QRCodeMixin');

    const TimesheetConfigQRCodeMixin = Object.assign({}, QRCodeMixin, {
        events: _.extend({}, QRCodeMixin.events, {
            'click .o_config_app_store, .o_config_play_store': '_onClickTSAppStoreIcon',
        }),
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickTSAppStoreIcon(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            const googleUrl = "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets";
            const appleUrl = "https://apps.apple.com/be/app/awesome-timesheet/id1078657549";
            const url = ev.target.classList.contains("o_config_play_store") ? googleUrl : appleUrl;
            this._openQRCodeScanner(url, 'TimeSheet App');
        },
    });

    const TimesheetConfigFormRenderer = BaseSetting.Renderer.extend({}, TimesheetConfigQRCodeMixin, {
        events: _.extend({}, TimesheetConfigQRCodeMixin.events, BaseSetting.Renderer.prototype.events),
    });

    const BaseSettingView = viewRegistry.get('base_settings');
    var TimesheetConfigFormView = BaseSettingView.extend({
        config: _.extend({}, BaseSettingView.prototype.config, {
            Renderer : TimesheetConfigFormRenderer,
        }),
    });

    viewRegistry.add('base_settings', TimesheetConfigFormView);

    return { TimesheetConfigQRCodeMixin, TimesheetConfigFormRenderer, TimesheetConfigFormView };

});
