
/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {

    async pay() {
        var self = this;
           let order = this.env.services.pos.getOrder();
           let lines = order.getOrderlines();
           let pos_config = this.pos;
           let call_super = true;
           var config_id=self.env.services.pos.config.id;
           let prod_used_qty = {};
           let restrict = false;
           if(this.env.services.pos.config.restrict_zero_qty){
               for (let line of lines) {
                   let prd = line.product_id;
                   if (prd.type == 'consu'){
                       if(prd.id in prod_used_qty){
                           let old_qty = prod_used_qty[prd.id][1];
                           prod_used_qty[prd.id] = [prd.qty_available,line.qty+old_qty]
                       }else{
                           prod_used_qty[prd.id] = [prd.qty_available,line.qty]
                       }
                   }
                   if (prd.type == 'consu'){
                       if(prd.qty_available <= 0){
                           restrict = true;
                           call_super = false;
                           let warning = prd.display_name + ' is out of stock.';
                           this.dialog.add(AlertDialog, {
                                title: _t("Zero Quantity Not allowed"),
                                body: _t(warning),
                           });
                       }
                   }
               }

           if(restrict === false){
               for (let [i, pq] of Object.entries(prod_used_qty)) {
                    let product = self.models['product.product'].getBy('id', parseInt(i));
                     let check = pq[0] - pq[1];
                     let warning = product.display_name + ' is out of stock.';
                     if (product.type == 'consu'){
                         if (check < 0){
                            call_super = false;
                             this.dialog.add(AlertDialog, {
                                title: _t('Deny Order'),
                                body: _t(warning),
                             });
                         }
                     }
               }
           }
        }
       if(call_super){
           super.pay();
       }
    },

});