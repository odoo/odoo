odoo.define('flexipharmacy.UnlockPosScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useState } = owl.hooks;
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');

    class UnlockPosScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ lock: false});
        }
        async toggle(key) {
            const { confirmed, payload } = await this.showPopup('NumberPopup', {
                isPassword: true,
                title: 'Security PIN',
            });
            if (confirmed){
                var user = this.env.pos.get_cashier();
                if (this.env.pos.config.module_pos_hr){
                    if(user && !user.pin){
                        alert("Please Set Security Pin for Particular Employee !");
                        return
                    }
                }else{
                    if(user && this.env.pos.user.pin){
                        user.pin = Sha1.hash(this.env.pos.user.pin)
                    }else{
                        alert("Please Set Security Pin for Particular User !");
                        return
                    }
                }
                var encrypt_password = Sha1.hash(payload)
                if(user.pin == encrypt_password){
                    var params = {
                        model: 'pos.session',
                        method: 'write',
                        args: [this.env.pos.pos_session.id,{'is_lock_screen' : false}],
                    }
                    rpc.query(params, {async: false}).then(function(result){})
                    $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
                    $('.freeze_screen').removeClass("active_state");
                    $('.unlock_button').css('display','none');
                }
                else{
                    $('.unlock_button').css('display','block');
                    $('.freeze_screen').addClass("active_state");
                    $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
                }
            }
        }
    }
    UnlockPosScreen.template = 'UnlockPosScreen';

    Registries.Component.add(UnlockPosScreen);

    return UnlockPosScreen;
});
