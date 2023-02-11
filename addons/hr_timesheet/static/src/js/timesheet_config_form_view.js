odoo.define('hr_timesheet.res.config.form', function (require) {
    "use strict";

    const core = require('web.core');
    const config = require('web.config');
    const Dialog = require('web.Dialog');
    const viewRegistry = require('web.view_registry');
    const BaseSetting = require('base.settings');
    const QWeb = core.qweb;
    
    const _t = core._t;

    const TimesheetConfigQRCodeDialog = Dialog.extend({
        /**
         * @override
         */
        init: function (parent, url) {
            this.url = _.str.sprintf("/report/barcode/?type=QR&value=%s&width=256&height=256&humanreadable=1", url);
            this._super(parent, {
                title: _t('Download our App'),
                buttons: [{
                    text: _t('View App'),
                    classes: 'btn-primary',
                    click: function() {
                        window.open(url, '_blank');
                    }
                }, {
                    text: _t('Discard'),
                    close: true
                }],
                $content: QWeb.render('hr_timesheet_qr_code', {widget: this})
            });
        },
    });

    const TimesheetConfigQRCodeMixin = {
        async _renderView() {
            const self = this;
            await this._super(...arguments);
            const google_url = "https://play.google.com/store/apps/details?id=com.odoo.OdooTimesheets";
            const apple_url = "https://apps.apple.com/be/app/awesome-timesheet/id1078657549";
            this.$el.find('img.o_config_app_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    new TimesheetConfigQRCodeDialog(this, apple_url).open();
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: apple_url});
                }
            });
            this.$el.find('img.o_config_play_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    new TimesheetConfigQRCodeDialog(this, google_url).open();
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

    return {TimesheetConfigQRCodeDialog, TimesheetConfigQRCodeMixin, TimesheetConfigFormRenderer, TimesheetConfigFormView};

});
