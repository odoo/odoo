odoo.define('flexipharmacy.PharmacyDetailSidebar', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState, useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    class PharmacyDetailSidebar extends PosComponent { 
        constructor() {
            super(...arguments);
            useListener('move-product', () => this.MoveOnProductFullScreen());
            useListener('refill-medicine-screen', () => this.RefillMedicineScreen());
            useListener('close-side-sub-menu', () => this.toggle('flag'));
            useListener('order-summary-popup', this.ShowOrderSummaryPopup);
            useListener('product-summary-popup', this.ShowProductSummaryPopup);
            useListener('payment-summary-popup', this.ShowPaymentSummaryPopup);
            useListener('audit-report-popup', this.ShowAuditReportPopup);
            useExternalListener(window, 'click', this._hideOptions);
            this.state = useState({ flag: false, componentFlag: false});
        }
        _hideOptions(event){
            if ($(event.target).attr('id')){
                if($(event.target).attr('id') == 'sidebar-wrapper' || $(event.target).attr('id') == 'pos_reports' || $(event.target).attr('id') == 'product-screen' || $(event.target).attr('id') == 'pos_reports' || $(event.target).attr('id') == 'order_summary' || $(event.target).attr('id') == 'order_current_session_report' || $(event.target).attr('id') == 'product_summary' || $(event.target).attr('id') == 'payment_summary' || $(event.target).attr('id') == 'audit_report'|| $(event.target).attr('class') === 'fa fa-angle-down' || $(event.target).attr('class') === 'fa fa-angle-right' || $(event.target).attr('class') === 'sidebar-brand' || $(event.target).attr('class') === 'date' || $(event.target).attr('id') === 'states' || $(event.target).attr('id') === 'no_of_copies' || $(event.target).attr('class') === 'fa fa-sticky-note' || $(event.target).attr('id') === 'no_of_summary' || $(event.target).attr('id') === 'order_end_date' || $(event.target).attr('id') === 'order_start_date' || $(event.target).attr('id') === 'start_date' || $(event.target).attr('id') === 'end_date' || $(event.target).attr('id') === 'pay_start_date' || $(event.target).attr('id') === 'pay_end_date'){
                    return
                }else {
                    this.trigger('close-side-menu')
                    return
                }
            }else{
                if(!$(event.target).attr('class') || $(event.target).attr('id') == 'pos_reports' || $(event.target).attr('id') == 'product-screen' || $(event.target).attr('id') == 'pos_reports' || $(event.target).attr('id') == 'order_summary' || $(event.target).attr('id') == 'order_current_session_report' || $(event.target).attr('id') == 'product_summary' || $(event.target).attr('id') == 'payment_summary' || $(event.target).attr('id') == 'audit_report'|| $(event.target).attr('class') === 'fa fa-angle-down' || $(event.target).attr('class') === 'fa fa-angle-right' || $(event.target).attr('class') === 'sidebar-brand' || $(event.target).attr('class') === 'date' || $(event.target).attr('id') === 'states' || $(event.target).attr('id') === 'no_of_copies' || $(event.target).attr('class') === 'fa fa-sticky-note' || $(event.target).attr('class') === 'slider round' || $(event.target).attr('class') === 'button report-button' || $(event.target).attr('class') === 'button report-button active' || $(event.target).attr('class') === 'modal-dialog' || $(event.target).attr('class') === 'footer' || $(event.target).attr('class') === 'title drag-handle' || $(event.target).attr('class') === 'button confirm'|| $(event.target).attr('class') === 'title-separator' || $(event.target).attr('class') === 'summary_date_div' || $(event.target).attr('class') === 'summary_option_container' || $(event.target).attr('class') === 'container_summary_popup' || $(event.target).attr('class') === 'summary_contain_div1' || $(event.target).attr('class') === 'popup' || $(event.target).attr('class') === 'start_date' || $(event.target).attr('class') === 'end_date' || $(event.target).attr('class') === 'summary_main_div' || $(event.target).attr('class') === 'date blank_validation_input'){
                    return
                }else {
                    this.trigger('close-side-menu')
                }
            }
            if ($(event.target).attr('class') === 'fa fa-th-large fa-lg'){
                this.trigger('close-side-menu')
            }
        }
        get imageUrl() {
            const user = this.env.pos.user;
            return '/web/image?model=res.users&field=image_1920&id='+user.id+'&write_date='+user.write_date+'&unique=1';
        }
        async ShowOrderSummaryPopup(){
            var self = this;
            var first_date_of_month = "";
            var today_date = "";
            if (this.env.pos.config.order_current_month_date){
                first_date_of_month = moment().startOf('month').format('YYYY-MM-DD');
                today_date = moment().format('YYYY-MM-DD');
            }
            const { confirmed, payload: popup_data } = await this.showPopup('OrderSummaryPopup', {
                title: this.env._t('Order Summary'),
                StartDate: first_date_of_month,
                EndDate: today_date,
                OrderSelectType: "",
                OrderNumberReceipt: 1,
            });
            if (confirmed) {
                var self = this;
                var order = self.env.pos.get_order();
                var report_value = [];

                if (popup_data.OrderSummary){
                    report_value.push('order_summary_report')
                }
                if (popup_data.CategorySummary){
                    report_value.push('category_summary_report')
                }
                if (popup_data.PaymentSummary){
                    report_value.push('payment_summary_report')
                }

                var val = {
                    'state' : popup_data.OrderSelectType,
                    'summary': report_value
                };
                if(popup_data.CurrentSession){
                    var pos_session_id = self.env.pos.pos_session.id;
                    val['session_id']= pos_session_id
                    self.env.pos.order_print_date = false;
                } else {
                    val['start_date']= popup_data.StartDate,
                    val['end_date']= popup_data.EndDate,
                    self.env.pos.order_print_date = true;
                    self.env.pos.order_date = [ popup_data.StartDate, popup_data.EndDate ];
                }
                if(val && !$.isEmptyObject(val)) {
                    await rpc.query({
                        model: 'pos.order',
                        method: 'order_summary_report',
                        args: [val],
                    }, {async: false}).then(async function(res){
                        if(res){
                            order.set_number_of_print(Number(popup_data.OrderNumberReceipt) || 1)
                            self.env.pos.state = false;
                            if(res.state){
                                self.env.pos.state = true
                            }
                            if(Object.keys(res.category_report).length == 0 &&
                                Object.keys(res.order_report).length == 0 &&
                                Object.keys(res.payment_report).length == 0){
                                    self.env.pos.db.notification('danger',self.env._t("No records found!"));
                                    
                            }else{
                                self.env.pos.total_category_amount = 0.00;
                                self.env.pos.total_amount = 0.00;
                                order.set_order_list(res);
                                if(res.category_report){
                                    if(self.env.pos.state){
                                        _.each(res.category_report, function(value,key) {
                                            self.env.pos.total_category_amount += value[1];
                                        });
                                    }
                                }
                                if(res.payment_report){
                                    if(self.env.pos.state){
                                        _.each(res.payment_report, function(value,key) {
                                            self.env.pos.total_amount += value;
                                        });
                                    }
                                }
                                var category_data, order_data, payment_data = false;
                                if(Object.keys(order.get_order_list().order_report).length > 0 ){
                                    order_data = order.get_order_list()['order_report']
                                }
                                if(Object.keys(order.get_order_list().category_report).length > 0 ){
                                    category_data = order.get_order_list()['category_report']
                                }
                                if(Object.keys(order.get_order_list().payment_report).length > 0 ){
                                    payment_data = order.get_order_list()['payment_report']
                                }
                                var use_posbox = self.env.pos.config.is_posbox && (self.env.pos.config.iface_print_via_proxy);
                                if (use_posbox || self.env.pos.config.other_devices) {
                                    const report = self.env.qweb.renderToString('OrderSummaryReceipt',{props: {
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'OrderReportData': order_data,
                                        'CategoryReportData': category_data,
                                        'PaymentReportData': payment_data
                                    }});
                                    const printResult = await self.env.pos.proxy.printer.print_receipt(report);
                                    if (!printResult.successful) {
                                        await self.showPopup('ErrorPopup', {
                                            title: printResult.message.title,
                                            body: printResult.message.body,
                                        });
                                    } 
                                } else {
                                    self.showScreen('ReceiptScreen', {
                                        'check':'from_order_summary',
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'OrderReportData': order_data,
                                        'CategoryReportData': category_data,
                                        'PaymentReportData': payment_data
                                    });
                                }
                            }
                        }
                    });
                }
            }
            this.trigger('close-side-menu')
        }
        async ShowProductSummaryPopup(){
            var self = this;
            var first_date_of_month = "";
            var today_date = "";
            if (this.env.pos.config.product_current_month_date){
                first_date_of_month = moment().startOf('month').format('YYYY-MM-DD');
                today_date = moment().format('YYYY-MM-DD');
            }
            const { confirmed, payload: popup_data } = await this.showPopup('ProductSummaryPopup', {
                title: this.env._t('Product Summary'),
                StartDate: first_date_of_month,
                EndDate: today_date,
                ProdNumberReceipt: 1,
            });
            if (confirmed) {
                var self = this;
                var order = self.env.pos.get_order();
                var report_value = [];

                if(popup_data.ProductSummary){
                    report_value.push('product_summary')
                }
                if(popup_data.CategorySummary){
                    report_value.push('category_summary')
                }
                if(popup_data.PaymentSummary){
                    report_value.push('payment_summary')
                }
                if(popup_data.LocationSummary){
                    report_value.push('location_summary')
                }
                var val = {'summary': report_value};

                if(popup_data.CurrentSession){
                    var pos_session_id = self.env.pos.pos_session.id;
                    val['session_id']=pos_session_id
                    self.env.pos.print_date = false;
                } else {
                    val['start_date']= popup_data.StartDate
                    val['end_date']= popup_data.EndDate
                    self.env.pos.print_date = true;
                    self.env.pos.date_information = [ popup_data.StartDate, popup_data.EndDate ];
                }
                if(val && !$.isEmptyObject(val)) {
                    await rpc.query({
                        model: 'pos.order',
                        method: 'product_summary_report',
                        args: [val],
                    }, {async: false}).then(async function(res){
                        if(res){
                            order.set_number_of_print(Number(popup_data.ProdNumberReceipt) || 1)
                            if(Object.keys(res.category_summary).length == 0 && Object.keys(res.product_summary).length == 0 &&
                                Object.keys(res.location_summary).length == 0 && Object.keys(res.payment_summary).length == 0){
                                self.env.pos.db.notification('danger',self.env._t("No records found!"));
                            } else{
                                self.env.pos.product_total_qty = 0.00;
                                self.env.pos.category_total_qty = 0.00;
                                self.env.pos.payment_summary_total = 0.00;
                                if(res.product_summary){
                                    _.each(res.product_summary, function(value,key){
                                        self.env.pos.product_total_qty += value;
                                    });
                                }
                                if(res.category_summary){
                                    _.each(res.category_summary, function(value,key) {
                                        self.env.pos.category_total_qty += value;
                                    });
                                }
                                if(res.payment_summary){
                                    _.each(res.payment_summary, function(value,key) {
                                        self.env.pos.payment_summary_total += value;
                                    });
                                }
                                order.set_product_summary_report(res);
                                var product_summary_data, category_summary_data, payment_summary_data, location_summary_data = false;
                                var product_summary_key = Object.keys(order.get_product_summary_report()['product_summary']);
                                if(product_summary_key.length > 0){
                                    product_summary_data = order.get_product_summary_report()['product_summary'];
                                }
                                var category_summary_key = Object.keys(order.get_product_summary_report()['category_summary']);
                                if(category_summary_key.length > 0){
                                    category_summary_data = order.get_product_summary_report()['category_summary'];
                                }
                                var payment_summary_key = Object.keys(order.get_product_summary_report()['payment_summary']);
                                if(payment_summary_key.length > 0){
                                    payment_summary_data = order.get_product_summary_report()['payment_summary'];
                                }
                                var location_summary_key = Object.keys(order.get_product_summary_report()['location_summary']);
                                if(location_summary_key.length > 0){
                                    location_summary_data = order.get_product_summary_report()['location_summary'];
                                }
                                var use_posbox = self.env.pos.config.is_posbox && (self.env.pos.config.iface_print_via_proxy);
                                if (use_posbox || self.env.pos.config.other_devices) {
                                    const report = self.env.qweb.renderToString('ProductSummaryReceipt',{props: {
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'ProductSummaryData': product_summary_data,
                                        'CategorySummaryData': category_summary_data,
                                        'PaymentSummaryData': payment_summary_data,
                                        'LocationSummaryData': location_summary_data
                                    }});
                                    const printResult = await self.env.pos.proxy.printer.print_receipt(report);
                                    if (!printResult.successful) {
                                        await self.showPopup('ErrorPopup', {
                                            title: printResult.message.title,
                                            body: printResult.message.body,
                                        });
                                    } 
                                } else {
                                    self.showScreen('ReceiptScreen', {
                                        'check':'from_product_summary',
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'ProductSummaryData': product_summary_data,
                                        'CategorySummaryData': category_summary_data,
                                        'PaymentSummaryData': payment_summary_data,
                                        'LocationSummaryData': location_summary_data
                                    });
                                }
                            }
                        }
                    });
                }
            }
            this.trigger('close-side-menu')
        }
        async ShowPaymentSummaryPopup(){
            var self = this;
            var first_date_of_month = "";
            var today_date = "";
            if (this.env.pos.config.product_current_month_date){
                first_date_of_month = moment().startOf('month').format('YYYY-MM-DD');
                today_date = moment().format('YYYY-MM-DD');
            }
            const { confirmed, payload: popup_data } = await this.showPopup('PaymentSummaryPopup', {
                title: this.env._t('Payment Summary'),
                StartDate: first_date_of_month,
                EndDate: today_date,
            });
 
            if (confirmed) {
                var self = this;
                var order = self.env.pos.get_order();
                var val = {
                    'summary': popup_data.PaymentSelectData,
                };
                if(popup_data.CurrentSession){
                    var pos_session_id = self.env.pos.pos_session.id;
                    val['session_id']= pos_session_id
                    self.env.pos.payment_print_date = false;
                } else{
                    val['start_date']= popup_data.StartDate
                    val['end_date']= popup_data.EndDate
                    self.env.pos.payment_print_date = true;
                    self.env.pos.payment_date = [ popup_data.StartDate, popup_data.EndDate ];
                }
                if (val && !$.isEmptyObject(val)) {
                    await rpc.query({
                        model: 'pos.order',
                        method: 'payment_summary_report',
                        args: [val],
                    }, {async: false}).then(async function(res){
                        if(res){
                            if(Object.keys(res.journal_details).length == 0 && Object.keys(res.salesmen_details).length == 0){
                                alert("No records found!");
                            } else{
                                order.set_number_of_print(Number(popup_data.PaymentNumberReceipt) || 1)
                                self.env.pos.print_date = false;
                                var journal_summary_data, sales_summary_data, total_summary_data = false;
                                order.set_sales_summary_val(res);
                                var journal_key = Object.keys(order.get_sales_summary_val()['journal_details']);
                                if (journal_key.length > 0){
                                    journal_summary_data = order.get_sales_summary_val()['journal_details'];
                                }
                                var sales_key = Object.keys(order.get_sales_summary_val()['salesmen_details']);
                                if (sales_key.length > 0){
                                    sales_summary_data = order.get_sales_summary_val()['salesmen_details'];
                                }
                                var total = Object.keys(order.get_sales_summary_val()['summary_data']);
                                if (total.length > 0){
                                    total_summary_data = order.get_sales_summary_val()['summary_data'];
                                }
                                var use_posbox = self.env.pos.config.is_posbox && (self.env.pos.config.iface_print_via_proxy);
                                if (use_posbox || self.env.pos.config.other_devices) {
                                    const report = self.env.qweb.renderToString('PaymentSummaryReceipt',{props: {
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'JournalReportData': journal_summary_data,
                                        'SalesReportData': sales_summary_data,
                                        'TotalSummaryData': total_summary_data,
                                    }});
                                    const printResult = await self.env.pos.proxy.printer.print_receipt(report);
                                    if (!printResult.successful) {
                                        await self.showPopup('ErrorPopup', {
                                            title: printResult.message.title,
                                            body: printResult.message.body,
                                        });
                                    } 
                                } else {
                                    self.showScreen('ReceiptScreen', {
                                        'check':'from_payment_summary',
                                        'values': val,
                                        'pos': self.env.pos,
                                        'receipt': order.getOrderReceiptEnv().receipt,
                                        'JournalReportData': journal_summary_data,
                                        'SalesReportData': sales_summary_data,
                                        'TotalSummaryData': total_summary_data,
                                    });
                                }
                            }
                        }
                    });
                }
            }
            this.trigger('close-side-menu')
        }
        async ShowAuditReportPopup(){
            const { confirmed, payload } = await this.showPopup('AuditReportPopup', {
                title: this.env._t('Audit Report'),
            });
            this.trigger('close-side-menu')
        }
        async MoveOnProductFullScreen(){
            this.trigger('close-side-menu')
            this.showScreen('ProductDetailScreen');
        }
        async RefillMedicineScreen(){
            this.trigger('close-side-menu')
            this.showScreen('RefillMedicineScreen');
        }
        toggle(key) {
            this.state[key] = !this.state[key];
        }
    }
    PharmacyDetailSidebar.template = 'PharmacyDetailSidebar';

    Registries.Component.add(PharmacyDetailSidebar);

    return PharmacyDetailSidebar;
});
 