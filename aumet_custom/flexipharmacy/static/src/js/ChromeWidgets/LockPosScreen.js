odoo.define('flexipharmacy.LockPosScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useState } = owl.hooks;
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');

    class LockPosScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ lock: this.env.pos.pos_session.is_lock_screen});
            this.ScreenLockCheck()
        }
        toggle(event, times, undefined) {
            var params = {
                model: 'pos.session',
                method: 'write',
                args: [this.env.pos.pos_session.id,{'is_lock_screen' : true}],
            }
            rpc.query(params, {async: false}).then(function(result){})
            $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
            $('.freeze_screen').addClass("active_state");
            $(".unlock_button").fadeIn(2000);
            $('.unlock_button').css('display','block');
        }
        ScreenLockCheck(){
            if (this.state.lock){
                $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
                $('.freeze_screen').addClass("active_state");
                $(".unlock_button").fadeIn(2000);
                $('.unlock_button').css('display','block');                
            }else{
                $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
                $('.freeze_screen').removeClass("active_state");
                $('.unlock_button').css('display','none');
            }
        }
    }
    LockPosScreen.template = 'LockPosScreen';

    Registries.Component.add(LockPosScreen);

    return LockPosScreen;
});
