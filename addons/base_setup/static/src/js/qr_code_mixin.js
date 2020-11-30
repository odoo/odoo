odoo.define('base_setup.QRCodeMixin', function (require) {
    "use strict";

    const core = require('web.core');
    const config = require('web.config');

    const _t = core._t;

    const QRCodeMixin = {
        events: {
            'click .o_base_setup_app_store, .o_base_setup_play_store': '_onClickAppStoreIcon',
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickAppStoreIcon(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            const googleUrl = "https://play.google.com/store/apps/details?id=com.odoo.mobile";
            const appleUrl = "https://apps.apple.com/be/app/odoo/id1272543640";
            const url = ev.target.classList.contains("o_base_setting_play_store") ? googleUrl : appleUrl;
            this._openQRCodeScanner(url)
        },
        /**
         * @private
         * @param {string} url
         * @param {string} appName
         */
        _openQRCodeScanner(url, appName='Odoo App') {
            if (!config.device.isMobile) {
                const actionDesktop = {
                    name: _t('Download our Mobile App'),
                    type: 'ir.actions.client',
                    tag: 'qr_code_modal',
                    target: 'new',
                    appName: _t(appName),
                };
                this.do_action(_.extend(actionDesktop, {params: {'url': url}}));
            } else {
                this.do_action({type: 'ir.actions.act_url', url: url});
            }
        },

    };

    return QRCodeMixin;

});
