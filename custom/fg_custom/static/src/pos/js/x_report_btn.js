odoo.define('fg_custom.XReportButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');

    class XReportButton extends PosComponent {
        async onClick() {
            try {
                if (this.env.pos && this.env.pos.config && this.env.pos.config.current_session_id && this.env.pos.config.current_session_id.length > 0) {
                    await this.env.pos.do_action('fg_custom.x_pos_report', {
                        additional_context: {
                            active_ids: [this.env.pos.config.current_session_id[0]],
                        },
                    });
                }else{
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Session Is Not Available.'),
                    });
                }
            } catch (error) {
                if (error instanceof Error) {
                    throw error;
                } else {
                    // NOTE: error here is most probably undefined
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to download invoice.'),
                    });
                }
            }
        }
    }

    XReportButton.template = 'XReportButton';

    Registries.Component.add(XReportButton);

    return XReportButton;
});
