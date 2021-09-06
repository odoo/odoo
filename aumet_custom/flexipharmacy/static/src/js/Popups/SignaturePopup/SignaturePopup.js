odoo.define('aces_pos_signature.SignaturePopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class SignaturePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }
        mounted(){
            if(this.env.pos.get_order().get_raw_sign()){
                $('#signature').jSignature({ lineWidth: 1, width: 400, height: 200 });
                let signData = this.env.pos.get_order().get_raw_sign();
                $('#signature').jSignature('setData', 'data:' + signData.join(','));
            }else{
                $('#signature').jSignature({ lineWidth: 1, width: 400, height: 200 });
            }
        }
        getPayload(){
            return {'base30': $("#signature").jSignature("getData", "base30"),
                    'base64':$("#signature").jSignature("getData", "image")};
        }
        clear(){
            this.env.pos.get_order().set_sign(null);
            this.env.pos.get_order().get_raw_sign(null);
            $("#signature").jSignature("reset");
        }
    }

    SignaturePopup.template = 'SignaturePopup';

    SignaturePopup.defaultProps = {
        confirmText: 'Apply',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(SignaturePopup);

    return SignaturePopup;
});
