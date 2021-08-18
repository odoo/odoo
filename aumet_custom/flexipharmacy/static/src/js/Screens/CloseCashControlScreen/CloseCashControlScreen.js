odoo.define('flexipharmacy.CloseCashControlScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;
    var rpc = require('web.rpc');
    var framework = require('web.framework');

    class CloseCashControlScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
            this._id = 0;
            this.closing_difference = this.props.sessionData[0].cash_register_difference;
            useListener('close-closing-cash-control', this.close);
            useListener('remove-closing-line', () => this.removeLine(event));
            useListener('closing-main_total',this._updateMainTotal);
            this.state = useState({ closeInputLines:[], closeTotal:0,showCloseStaticLines : true,
                                    staticDataCloseScreen : this._dummyData(),
                                    closingDifference: this.closing_difference});
        }
        _updateMainTotal(){
            let total = 0;
            _.each(this.state.closeInputLines, function(line){
                total += line.line_total;
            });
            this.state.closeTotal = total;
            this.state.closingDifference = this.closing_difference + total;
        }
        _nextId() {
            return {
                coin_value:0,
                number_of_coins:0,
                line_total :0,
                _id: this._id++,
            };
        }
        _dummyData(){
            return [
                {coin_value:10,number_of_coins:5,},
                {coin_value:20, number_of_coins:4},
                {coin_value:50, number_of_coins:2},
                {coin_value:100, number_of_coins:2},
                {coin_value:200, number_of_coins:3},
            ];
        }
        createNewCloseInputLine() {
            this.state.closeInputLines.push(this._nextId());
            this.state.showCloseStaticLines = false;
        }
        removeLine(event) {
            this.state.closeInputLines = this.state.closeInputLines.filter((item) => item._id !== event.detail._id);
            this._updateMainTotal();
            if((this.state.closeInputLines).length == 0){
                this.state.showCloseStaticLines = true;
            }
        }
        onClickCloseSession(){
            var self = this;
            var dict = [];
            _.each(self.state.closeInputLines, function(line){
               if(line.line_total > 0){
                   dict.push({
                       'coin_value':line.coin_value,
                       'number_of_coins':Number(line.number_of_coins),
                       'subtotal':line.line_total,
                       'pos_session_id':self.env.pos.pos_session.id
                   })
               }
            });
            if(dict.length > 0){
                var CashControlLine = new Promise(function (resolve, reject) {
                    rpc.query({
                        model: 'pos.session',
                        method: 'cash_control_line',
                        args:[self.env.pos.pos_session.id,dict],
                    }).then(function(res){
                        resolve(res);
                    }).catch(function(){
                        console.log("\n\n Connection Lost !");
                    });
                })
                CashControlLine.then(function(res){
                    if(res){
                        self.check_validate_session();
                    }
                });
            } else {
                self.check_validate_session();
            }
        }

        async check_validate_session(){
            var self = this;
            if(self.state.closingDifference < 0){
                const { confirmed } = await self.showPopup('ConfirmPopup', {
                   title: self.env._t('Do you want to continue ?'),
                   body: self.env._t(
                        'There is a difference, do you want to continue ?'
                   ),
                });
                if(confirmed){
                    self.close_session();
                }
            }else{
               self.close;
               self.close_session();
            }
        }

        async closePosSession(){
            var params = {
                model: 'pos.session',
                method: 'custom_close_pos_session',
                args:[this.env.pos.pos_session.id]
            }
            return this.rpc(params, {async: false}).then(function(res){});
        }

        async generateZReport(){
            return this.env.pos.do_action('flexipharmacy.pos_z_report',{additional_context:{
                       active_ids:[this.env.pos.pos_session.id],
            }});
        }

        async generateReceipt(){
            var self = this;
            var report_name = "flexipharmacy.pos_z_thermal_report_template";
            var params = {
                model: 'ir.actions.report',
                method: 'get_html_report',
                args: [[self.env.pos.pos_session.id], report_name],
            }
            return self.rpc(params, {async: false}).then(function(report_html){
                if(report_html && report_html[0]){
                    self.env.pos.proxy.printer.print_receipt(report_html[0]);
                }
            });
        }
        async close_session() {
            framework.blockUI();
            await this.closePosSession();
            if(this.env.pos.config.z_report_pdf){
                await this.generateZReport();
            }
            if(this.env.pos.config.iface_print_via_proxy){
                await this.generateReceipt();
            }
            framework.unblockUI();
            this.trigger('close-pos');
        }
    }

    CloseCashControlScreen.template = 'CloseCashControlScreen';

    Registries.Component.add(CloseCashControlScreen);

    return CloseCashControlScreen;
});

