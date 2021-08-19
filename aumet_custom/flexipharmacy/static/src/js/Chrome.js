odoo.define('flexipharmacy.Chrome', function(require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');
    const { useRef } = owl.hooks;
    var cross_tab = require('bus.CrossTab').prototype;
    const rpc = require('web.rpc');
    var core = require('web.core');
    var session = require('web.session');
    var framework = require('web.framework');

    const AsplRetChromeInh = (Chrome) =>
        class extends Chrome {
            constructor() {
                super(...arguments);
                this.state.OrderCount = 0;
                this.state.showOrderPanel = false;
                this.RfidScaneCode = useRef('RfidScaneCoderef')
            }
            async start() {
                await super.start();
                core.bus.on('barcode_scanned', this, function (barcode) {
                    var RfidCode = {code: barcode, rfid:true}
                    if (this.RfidScaneCode.comp !== null){
                        this.RfidScaneCode.comp.barcodeCashierAction(RfidCode)
                    }
                });
                var user = this.env.pos.get_cashier();
                if(this.env.pos.pos_session.is_lock_screen){
                    $('.ClickLockButton').click();
                }
                if (this.env.pos.config.enable_automatic_lock) {
                    this._setIdleTimer();
                }
                await this._poolData();
                this.env.pos.set(
                    'selectedMaterialCategoryId',
                    this.env.pos.config.iface_start_categ_id
                        ? this.env.pos.config.iface_start_categ_id[0]
                        : 0
                );
            }
            _poolData(){
                this.env.services['bus_service'].updateOption('customer.display',session.uid);
                this.env.services['bus_service'].onNotification(this,this._onNotification);
                this.env.services['bus_service'].startPolling();
                // cross_tab._isRegistered = true;
                // cross_tab._isMasterTab = true;
            }
            _onNotification(notifications) {
                var self = this;
                for (var notif of notifications) {
                    if(notif[1].updeted_location_vals_qty){
                        for (var updeted_location_vals_qty of notif[1].updeted_location_vals_qty) {
                            var product = self.env.pos.db.get_product_by_id(updeted_location_vals_qty.product_id)
                            if (updeted_location_vals_qty.location_id === self.env.pos.get_order().get_product_location().id) {
                                product.qty_available = updeted_location_vals_qty.quantity
                            }
                        }
                    }
                    let previous_orders = self.env.pos.db.get_orders_list();
                    if (notif[1] && notif[1].cancelled_order){
                        previous_orders = previous_orders.filter(function(obj){
                            return obj.id !== notif[1].cancelled_order[0].id;
                        });
                        self.env.pos.db.add_orders(previous_orders);
                        const orderFiltered = previous_orders.filter(order => order.state == "draft");
                        self.env.pos.db.add_draft_orders(orderFiltered);
                        this.state.OrderCount = orderFiltered.length;
                        this.render();
                    }else if(notif[1] && notif[1].new_pos_order){
                        previous_orders.push(notif[1].new_pos_order[0]);
                        var obj = {};
                        for ( var i=0, len=previous_orders.length; i < len; i++ ){
                            obj[previous_orders[i]['id']] = previous_orders[i];
                        }
                        previous_orders = new Array();
                        for ( var key in obj ){
                           previous_orders.push(obj[key]);
                        }
                        previous_orders.sort(function(a, b) {
                          return b.id - a.id;
                        });
                        self.env.pos.db.add_orders(previous_orders);
                        const orderFiltered = previous_orders.filter(order => order.state == "draft");
                        self.env.pos.db.add_draft_orders(orderFiltered);
                        this.state.OrderCount = orderFiltered.length;
                        this.render();
                    }
                    var order = self.env.pos.get_order();
                    if(notif[1].rating && order){
                        order.set_rating(notif[1].rating);
                    }else if(notif[1].partner_id){
                        var partner_id = notif[1].partner_id;
                        var partner = self.env.pos.db.get_partner_by_id(partner_id);
                        if(partner && order){
                            order.set_client(partner);
                        }else{
                            if(partner_id){
                                var fields = _.find(self.env.pos.models,function(model){
                                                 return model.model === 'res.partner';
                                             }).fields;
                                var params = {
                                    model: 'res.partner',
                                    method: 'search_read',
                                    fields: fields,
                                    domain: [['id','=',partner_id]],
                                }
                                rpc.query(params, {async: false})
                                .then(function(partner){
                                    if(partner && partner.length > 0 && self.env.pos.db.add_partners(partner)){
                                        order.set_client(partner[0]);
                                        self.env.pos.db.notification('success',self.env._t(partner[0].name+" is added successfully as a customer."));
                                    }else{
                                        alert("partner not loaded in pos.");
                                    }
                                });
                            }else{
                                console.info("Partner id not found!")
                            }
                        }
                    }
                    this.render();
                 }
            }
            _setIdleTimer() {
                if(this.env.pos.config.enable_automatic_lock){
                    var time_interval = this.env.pos.config.time_interval || 3;
                    var milliseconds = time_interval * 60000
                    setTimeout(() => {
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
                    }, milliseconds);
                }
            }
            // POS Close Session
            get startScreen() {
                if (this.env.pos.config.enable_close_session && this.env.pos.config.cash_control && this.env.pos.pos_session.state == 'opening_control' && this.env.pos.user.access_close_session) {
                    return { name: 'CashControlScreen'};
                } else {
                    return super.startScreen;
                }
            }

            async generateZReport(){
                return this.env.pos.do_action('flexipharmacy.pos_z_report',{additional_context:{
                           active_ids:[this.env.pos.pos_session.id],
                }});
            }

            async closePosSession(){
                var params = {
                    model: 'pos.session',
                    method: 'custom_close_pos_session',
                    args:[this.env.pos.pos_session.id]
                }
                return this.rpc(params, {async: false}).then(function(res){});
            }

            async generateReceipt(){
                var self = this;
                if(self.env.pos.config.other_devices){
                    var report_name = "flexipharmacy.pos_z_thermal_report_template";
                    var params = {
                        model: 'ir.actions.report',
                        method: 'get_html_report',
                        args: [[self.env.pos.pos_session.id], report_name],
                    }
                    rpc.query(params, {async: false})
                    .then(function(report_html){
                        if(report_html && report_html[0]){
                            self.env.pos.proxy.printer.print_receipt(report_html[0]);
                        }
                    });
                }
            }

            async _closePos() {
                if(this.env.pos.config.enable_close_session && this.env.pos.user.access_close_session){
                    var self = this;
                    if(self.mainScreen.name != 'CloseCashControlScreen'){
                        const { confirmed } = await self.showPopup('CloseSessionPopup');
                        if(confirmed){
                            if(self.env.pos.config.cash_control){
                                this.trigger('close-temp-screen');
                                self.get_session_data().then(function(session_data){
                                    self.showScreen('CloseCashControlScreen',{'sessionData': session_data});
                                });
                                return;
                            }else{
                                framework.blockUI();
                                await self.closePosSession();
                                if(self.env.pos.config.z_report_pdf){
                                    await self.generateZReport();
                                }
                                if(self.env.pos.config.iface_print_via_proxy){
                                    await self.generateReceipt();
                                }
                                framework.unblockUI();
                                super._closePos();
                            }
                        }else{
                            return;
                        }
                    }else{
                        await super._closePos();
                    }
                }
                else{
                    await super._closePos();
                }
            }

            get_session_data(){
                var self = this;
                var session_details = false;
                return new Promise(function (resolve, reject) {
                    var params = {
                        model: 'pos.session',
                        method: 'search_read',
                        domain: [['id', '=', self.env.pos.pos_session.id]],
                    }
                    rpc.query(params, {}).then(function (data) {
                        if(data){
                            session_details = data;
                            resolve(session_details);
                        } else {
                            reject();
                        }
                   }, function (type, err) { reject(); });
                });
            }
        }


    Registries.Component.extend(Chrome, AsplRetChromeInh);

    return Chrome;
});
