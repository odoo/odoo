/** @odoo-module */
import { ConfirmationDialog } from "@web/static/src/core";

odoo.define('jys_shopee.delete_confirmation',[], function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    console.log(FormController,'FormController = = = = = =');
    console.log(Dialog,'Dialog = = = = =');
    // FormController.include({
    //     _onButtonClicked: function (event) {
    //         var self = this;
    //         var def;
    //         console.log('MASOKKK??');
    //         if (event.data.attrs.name === 'action_delete_all_shopee_img') {
    //             def = Dialog.confirm(this, 'Are you sure you want to delete all Shopee images?', {
    //                 confirm_callback: function () {
    //                     self._rpc({
    //                         model: 'product.template',
    //                         method: 'action_delete_all_shopee_img',
    //                         args: [self.model.get(self.handle).data.id],
    //                     }).then(function () {
    //                         self.reload();
    //                     });
    //                 },
    //             });
    //         } else {
    //             def = this._super.apply(this, arguments);
    //         }
    //         return def;
    //     },
    // });
});
