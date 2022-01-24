odoo.define('fg_custom.FgChannelPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgChannelPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                x_ext_source: '',
            });
        }
        confirm() {
            return super.confirm();
        }

        getPayload() {
            return {
                x_ext_source: this.state.x_ext_source
            };
        }
    }
    FgChannelPopup.template = 'FgChannelPopup';
     FgChannelPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Channel'),
    };
    Registries.Component.add(FgChannelPopup);

    return FgChannelPopup;
});
