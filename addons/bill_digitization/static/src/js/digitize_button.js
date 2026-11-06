/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { patch } from "@web/core/utils/patch";
const { useState } = owl;
var rpc = require('web.rpc');
var core = require('web.core');
var _t = core._t;

patch(ListController.prototype, "DigitizeList", {
    /* Making button visibility false in default */
     async setup(){
     this.state = useState({
        button_state : false
     })
    this._super();
    /* Getting the value of the field */
    const digitizeBillParam = await rpc.query({
        model: 'ir.config_parameter',
        method: 'get_param',
        args: ['bill_digitization.digitize_bill'],
    });
    this.state.button_state = digitizeBillParam
    },
    /* Opening a wizard on button click */
    onClickDigitize() {
         this.actionService.doAction({
            name: _t("Upload Bill"),
            type: "ir.actions.act_window",
            res_model: "digitize.bill",
            view_type : 'form',
            view_mode : 'form',
            views: [[false, "form"]],
            target: 'new',
        });
    },
})
