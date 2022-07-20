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
                website_order_id: '',
            });
        }

        channelFgChange(event) {
            if (event.target.value == 'Website'){
                $("div.website_order_id").css('display','block');
            }else{
                $("div.website_order_id").css('display','none');
            }
        }

        confirm() {
            return super.confirm();
        }

        getPayload() {
            console.log('------getPayload-1111--', $("input[name='website_order_id']").val(), $("select[name='x_ext_source']").val(), this, this.state.x_ext_source, this.state.website_order_id)
            return {
                x_ext_source: $("select[name='x_ext_source']").val(),
                website_order_id: this.state.website_order_id
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
