odoo.define('hr_timesheet.res.config.form', function (require) {
    "use strict";

    const core = require('web.core');
    const config = require('web.config');
    const viewRegistry = require('web.view_registry');
    const BaseSetting = require('base.settings');
    
    const _t = core._t;

    const TimesheetConfigQRCodeMixin = {
        async _renderView() {
            const self = this;
            await this._super(...arguments);
            const google_url = "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets";
            const apple_url = "https://apps.apple.com/be/app/awesome-timesheet/id1078657549";
            const action_desktop = {
                name: _t('Download our App'),
                type: 'ir.actions.client',
                tag: 'timesheet_qr_code_modal',
                target: 'new',
            };
            this.$el.find('img.o_config_app_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    self.do_action(_.extend(action_desktop, {params: {'url': apple_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: apple_url});
                }
            });
            this.$el.find('img.o_config_play_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    self.do_action(_.extend(action_desktop, {params: {'url': google_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: google_url});
                }
            });
        },
    };


    var TimesheetConfigFormRenderer = BaseSetting.Renderer.extend(TimesheetConfigQRCodeMixin);
    const BaseSettingView = viewRegistry.get('base_settings');
    var TimesheetConfigFormView = BaseSettingView.extend({
        config: _.extend({}, BaseSettingView.prototype.config, {
            Renderer : TimesheetConfigFormRenderer,
        }),
    });

    viewRegistry.add('hr_timesheet_config_form', TimesheetConfigFormView);

    return {TimesheetConfigQRCodeMixin, TimesheetConfigFormRenderer, TimesheetConfigFormView};

});
