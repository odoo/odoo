odoo.define('base_hospital_management.pharmacy_dashboard_action', function (require) {
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var medicine=0;
    var sl_prod=0;
    var prod_uom=0;
    var next_line_prod=0;
    var currency=0;
    var quantity=0;
    var amount=0;
    var sub_t=0;
    var pro_list=[];
    var uom_lst= [];
    var tax_lst= [];
    var invoice_id=0;
    var tax_amount=0;
    var tax=0;
    localStorage.setItem('next_line_prod',next_line_prod);
    var PharmacyDashboard = AbstractAction.extend({
        template: 'PharmacyDashboard',
        init: function (parent, context) {
            this._super(parent, context);
        },
        //Events
        events: {
            'click .search_btn': 'fetch_patient_data',
            'click .home': 'create_order',
            'click .sale_orders': 'fetch_sale_orders',
            'click .medicine_search': 'fetch_medicine_data',
            'click .vaccine_search': 'fetch_vaccine_data',
            'click .clear_btn': 'clear_data',
            'click .row-click': 'click_op_row',
            'keydown .amount': 'next_line',
            'change .select_prod': '_onChange_prod_price',
            'change .qty': '_onChange_prod_qty',
            'click .home': 'fetch_product',
            'click .qty': 'fetch_uom',
            'change .home': 'fetch_tax',
            'click .create_sale_order': 'create_sale_order',
            'click .saleorder': 'createSaleOrder',
            'click .print_sale_order': 'PrintSaleOrder',
            'click .delete_row': 'DeleteRow',
            'click .order_row': 'viewOrder'
        },
        start: function () {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function () {
                self.create_order();
                self.fetch_product();
                self.fetch_uom();
                self.fetch_tax();
            })
        },
        //Method for viewing doctor's schedule
        viewOrder : function(ev) {
            var self = this;
            rpc.query({
                model: 'sale.order',
                method: 'search_read',
                args: [[['partner_id.patient_seq','not in', ['New', 'Employee', 'User']]], ['name', 'create_date', 'partner_id', 'amount_total',
                    'state']],
            }).then(function (result){
            var orderList = result;
            var record_id = parseInt(self.$(ev.target).data('index'))
            var record  = orderList[record_id];
            self.do_action({
                    name: "Sale Order",
                    type: 'ir.actions.act_window',
                    res_model: 'sale.order',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
            })
           })
        },
       //Fetch patient details
        fetch_patient_data: function () {
            var self = this;
            rpc.query({
                model: 'res.partner',
                method: 'action_get_patient_data',
                args: [self.$('#patient_search').val()],
            }).then(function (result) {
                self.$('#patient-name').text(`${result.name} - (${result.unique})`);
                self.$('#patient-title').text(result.name || '');
                self.$('#patient-code').text(result.unique || '');
                self.$('#patient-age').text(result.dob || '');
                self.$('#patient-blood').text(result.blood_group || '');
                self.$('#patient-blood').text(result.blood_group || '');
                self.$('#patient-gender').text(result.gender || '');
                self.$('#patient-image').attr('src', 'data:image/png;base64, ' + result.image_1920);
                if (result.name == 'Patient Not Found') {
                    self.$('#content_div').html('');
                    self.$('#medical_list').html('');
                    self.$('#hist_head').html('')
                    self.$('#patient-image').attr('src', 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png');
                }
                else {
                    self.$('#medical_list').html('');
                    self.$('#hist_head').html('')
                    self.$('#content_div').html('')
                    self.$('#medical_list').html(`
                    <div class="container" id="hist_head"
                        style="width:auto;margin-top:2px; height:230px;overflow-y: scroll;">
                    <h4 class="medical_items" style="margin-top:6px;">OP History</h4>
                    <table style="width:350px;" class="table striped">
                        <thead>
                            <tr>
                                <th>OP Code</th>
                                <th>Date</th>
                                <th>Doctor</th>
                            </tr>
                        </thead>
                        <tbody id="history"/>
                    </table>
                    </div>`);
                    result.history.forEach(res => {
                        $('#history').append(`<tr class="row-click"><td data-op_id=${res[0]}>${res[0]}</td><td data-op_id=${res[0]}>${res[1]}</td><td data-op_id=${res[0]}>${res[2]}</td></tr>`)
                    })
                }
            })
        },
        //Method fo creating a sale order for medicine
        create_order: function () {
             rpc.query({
                model: 'hospital.pharmacy',
                method: 'company_currency',
            }).then(function (result){
               self.$('#symbol'+ currency).text(result || '');
               self. $('#symbol').text(result || '');
            })
            self.$('#content_div').html(`<h1><center style="padding-top:20px;">Sale Order</center></h1>
                                     <div class="row" style="margin-left: 0px" id="op_table">
                                            <div class="col-m-12 col-md-12 col-lg-12">
                                                <label for="select_type">Name :</label>
                                                <input type="text"  style="max-width:100%;" id="patient-name" class="form-control" placeholder="Name"/>
                                                <label id="patient_label" for="sl_patient">Phone Number</label>
                                                <input type="tel" style="max-width:100%;" id="patient-phone" placeholder="Phone Number" class="form-control"/>
                                                <label for="o_patient-email">Email :</label>
                                                <input type="email" style="max-width:100%;min-height: 4rem;margin-bottom: 10px;" class="form-control" id="patient-mail" placeholder="Email"/>
                                                <label for="o_patient-dob">Date of Birth :</label>
                                                <input type="date" style="max-width:100%;" class="form-control" id="o_patient-dob" placeholder="Date of Birth"/>
                                                <label for="o_patient_bloodgroup">Gender :</label>
                                                    <input type="radio" class="form-check-input o_radio_input" checked="true" id="patient-gender" name="gender" value="male"/><label >Male</label>
                                                    <input type="radio" class="form-check-input o_radio_input" id="patient-gender" name="gender" value="female"/><label >Female</label>
                                                    <input type="radio" class="form-check-input o_radio_input" id="patient-gender" name="gender" value="other"/><label >Other</label></td></tr>
                                            </div>
                                     </div>
                                    </br>
                                    <div><center><h1>Medicine List</h1></center></div></br>
                                    <div class="container-tbl-medicine-list">
                                        <table class="tables tbl-medicine-list" id="table">
                                            <tr>
                                                <th>Name</th>
                                                <th>Quantity</th>
                                                <th>Unit Of Measure</th>
                                                <th>Price</th>
                                                <th>Sub Total(incl.Tax)</th>
                                                <th><th>
                                            </tr>
                                            <tbody id="bill_table" class="bill_tables">
                                                <tr class="tbl_row">
                                                    <td>
                                                        <select name="prod" id="sl${sl_prod}" class="form-control select_prod"/>
                                                    </td>
                                                    <td>
                                                        <input type="text" id="qty${quantity}"  class="form-control qty" style="width: 5vw;"/>
                                                    </td>
                                                    <td>
                                                        <select name="uom_sl" id="uom${prod_uom}" class="form-control select_uom"/>
                                                    </td>
                                                    <td>
                                                        <input type="number" readonly="" id="amt${amount}" class="form-control amount" style="width: 5vw;"/>
                                                    </td>

                                                    <td style="position:relative;">
                                                        <i id="symbol${currency}" style="position: absolute;left: 7px;top: 6px;"></i>
                                                        <input type="number" readonly="" id="sub_total${sub_t}" class="form-control sub_total" style="width: 5vw;padding-left:20px;"/>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <tr>
                                        <span class="g_total">  Grand Total : </span>
                                        <div style="float: left;width: auto;position: relative;padding-left: 0;margin-left: 0;">

                                            <i id="symbol" style="width: auto;position: absolute;top: 11px;left: 8px;">₹</i>
                                            <input readonly="" type="number" id="grand_total" class="form-control grand_total" style="width: 5vw;margin-left: 0px;margin: 6px 0px;padding-left: 21px;"></div>
                                        </div>

                                    </tr>
                                    <div class="btn-div">
                                        <button class="btn-primary create_sale_order">Create Sale Order</button>
                                        <button class="btn-primary print_sale_order">Print Sale Order</button>
                                    </div>
                                    `)
            self.$('.select_prod').html('')
            this.product_lst.forEach(element => {
                self.$('.select_prod').append(`
                    <option value="${element['id']}">${element.name}</option>
                `)
            })
            self.$('.select_uom').html('')
               if (this.uom_lst){
                    this.uom_lst.forEach(element => {
                        self.$('.select_uom').append(`
                            <option value="${element['id']}">${element.name}</option>
                    `)
               })
            }
        },
        //Method fo fetching all sale orders
        fetch_sale_orders: function () {
             rpc.query({
                model: 'sale.order',
                method: 'search_read',
                args: [[['partner_id.patient_seq','not in', ['New', 'Employee', 'User']]], ['name', 'create_date', 'partner_id', 'amount_total',
                    'state']],
            }).then(function (result){
                self.$('#content_div').html(``);
                var count = 0;
                self.$('#content_div').html(`
                    <h2 style="margin-top:2rem;">Sale Orders</h2>
                    <div style='height:572px; overflow-y: auto;'>
                    <table style="margin-top:30px;" id="order_items">
                       <tr>
                        <th>Number</th>
                        <th>Creation Date</th>
                        <th>Customer</th>
                        <th>Total</th>
                        <th>Status</th>
                    </tr>
                    </table></div>`);
                result.forEach(res => {
                    self.$('#order_items').append(`
                    <tr class="order_row" data-index=${count}>
                        <td data-index=${count}>${res.name || ''}</td>
                        <td data-index=${count}>${res.create_date || ''}</td>
                        <td data-index=${count}>${res.partner_id[1] || ''}</td>
                        <td data-index=${count}>${res.amount_total || 0}</td>
                        <td data-index=${count}>${res.state.toUpperCase() || ''}
                    </tr>
                        `);
                    count += 1;
                });
            });
        },
       //Add new line for entering all fields while clicking Enter.
        next_line: function (ev) {
            var sub_t_list=[]
            if (ev.key == 'Enter') {
                sl_prod=sl_prod+1;
                prod_uom=prod_uom+1;
                quantity=quantity+1;
                amount=amount+1;
                sub_t=sub_t+1;
                    next_line_prod=next_line_prod+1
                    var row='row_'+next_line_prod
                 rpc.query({
                    model: 'hospital.pharmacy',
                    method: 'company_currency',
                }).then(function (result){
                    self.$('#symbol'+currency).text(result || '');
                })
                    self.$('#bill_table').append(`
                        <tr class="tbl_row">
                            <td>
                                <select id="sl${sl_prod}" class="form-control select_prod" name="prod"/>
                            </td>
                            <td>
                                <input type="text"  id="qty${quantity}" class="form-control qty" style="width: 5vw;"/>
                            </td>
                            <td>
                                <select name="uom_sl" id="uom${prod_uom}" class="form-control select_uom"/>
                            </td>
                            <td>
                                <input type="number" id="amt${amount}" class="form-control amount" style="width: 5vw;"/>
                            </td>
                            <td>
                               <i id="symbol${currency}">
                               </i><input type="number" id="sub_total${sub_t}" class="form-control sub_total" style="width: 5vw;"/>
                            </td>
                            <td>
                               <button type="object" id="delete_row" class="form-control fa fa-times-circle delete_row"/>
                            </td>
                        </tr>`);
                    self.$('#sl'+sl_prod).html('')
                        this.product_lst.forEach(element => {
                            $('#sl'+sl_prod).append(`
                                <option value="${element['id']}">${element.name}</option>
                            `)
                     }),
                     self.$('#uom'+prod_uom).html('')
                      this.uom_lst.forEach(element => {
                         $('#uom'+prod_uom).append(`
                                    <option value="${element['id']}">${element.name}</option>
                         `)
                      })
            }
        },
        //Product list.
         product_lst :[],
            fetch_product: function (){
            var self = this;
            var result = rpc.query({
                model: 'product.product',
                method: 'search_read',
                kwargs: {domain: [['medicine_ok', '=', true]]},
            }).then(function (result) {
                self.product_lst=result
                self.create_order()
            })
        },
        //Fetch UOM of selected product
        fetch_uom: function (){
           var self = this;
           uom_lst= [];
           var result=rpc.query({
           model : 'uom.uom',
           method :'search_read',
           args:[''],
           }).then(function (result){
            self.uom_lst=result
           })
        },
        //Fetch tax amount of product.
        fetch_tax: function (){
           var self = this;
           tax_lst= [];
           var result=rpc.query({
           model : 'account.tax',
           method :'search_read',
           args:[''],
           }).then(function (result){
                self.tax_lst=result
           })
        },
        //Add tax amount of selected product with the unit price.
        _onChange_prod_price: function(ev) {
           var self = this;
           var prod_id = $(ev.target).val()
           var parent = $(ev.target).parent().parent()
           var table_row_amount = parent.children()[3]
           self.product_lst.forEach(element => {
                if (element.id == prod_id){
                    $(table_row_amount).children()[0].value = element.list_price
                    var result=rpc.query({
                        model : 'hospital.pharmacy',
                        method :'tax_amount',
                        args:[element.taxes_id],
                    }).then(function (result){
                            tax_amount = result.amount
                            self.$('.qty')[0].value = ""
                            self.$('#sub_total'+sub_t)[0].value =""
                    })
                }
            })
        },
        //Calculation of sub total and grand total based on product quantity
        _onChange_prod_qty: function(ev) {
            var self = this;
            var qty_id=$(ev.target).val()
            var sub_total=Number($("#amt"+amount).val()) +
            Number(self.$("#amt"+amount).val() * Number(tax_amount/100))
            self.$('#sub_total'+sub_t)[0].value = sub_total
            self.$('#grand_total')[0].value = Number(self.$('#sub_total'+sub_t)[0].value) * Number(qty_id)
        },
        //Create sale order for new medicines from pharmacy dashboard.
        create_sale_order: function() {
            var self = this
            let data_table = self.$('#bill_table');
            var data ={};
            data['name'] = self.$('#patient-name').val();
            data['phone'] = self.$('#patient-phone').val();
            data['email']=  self.$('#patient-mail').val();
            data['dob'] =  self.$('#patient-dob').val();
            data['products']= [];
            let hasInvalidQuantity = false;
            Array.prototype.forEach.call(data_table[0].children, function(element) {
                let qty = parseInt($(element)[0].children[1].firstElementChild.value) || 0;
                if (qty >= 1) {
                    let item = {
                        'prod': $(element)[0].children[0].firstElementChild.value,
                        'qty': qty,
                        'uom': $(element)[0].children[2].firstElementChild.value,
                        'price': $(element)[0].children[3].firstElementChild.value || 0
                    };
                    data['products'].push(item);
                } else {
                    hasInvalidQuantity = true;
                }
            });
            if (hasInvalidQuantity) {
                alert('Quantity must be greater than or equal to 1.');
                return;
            }
            rpc.query({
                model: 'hospital.pharmacy',
                method: 'create_sale_order',
                kwargs: data
            }).then(function (result) {
                 invoice_id = result.invoice_id
            })
        },
        //Print sale order
        PrintSaleOrder: function () {
            var self = this;
            if (invoice_id){
                self.do_action({
                    'type': 'ir.actions.act_url',
                    'url': `/report/pdf/account.report_invoice/${invoice_id}`,
                    'target': 'new',
                     })
            }
        },
        //Delete row
        DeleteRow: function (ev) {
            $(ev)[0].currentTarget.closest('tr').remove();
        },
        //Fetch medicine data while clicking Medicine button
        fetch_medicine_data: function () {
            var self = this;
            rpc.query({
                model: 'product.template',
                method: 'action_get_medicine_data',
                args: [],
            }).then(function (result) {
                self.$('#content_div').html(``);
                self.$('#content_div').html(`
                    <h2 style="margin-top:2rem;">Medicines</h2>
                    <div class="row medicines" id="med_items" style="height:600px; margin-left:2rem; width: 52rem; height:730px; overflow-y: scroll;">
                    </div>`);
                result.medicine.forEach(res => {
                    self.$('#med_items').append(`
                        <div class="card">
                            <img style="width:auto; height:99px;margin-top: 11px; display: grid;justify-content:center;" class="card-img-top" src="data:image/png;base64,${res[3]}"/>
                               <div class="card-body" style="margin-top: 10px;">
                                <h3 id="medicine_name" class="card-title">${res[0]}</h3>
                                <div style="float:left;width:100%;">
                                    <span style="float:left;">Price:</span>
                                    <p id="medicine_price" class="card-text" style="margin-top: auto; float:left;">${res[1]}</p>
                                </div>
                                <div style="float:left;">
                                    <span style="float:left;">Quantity:</span>
                                    <p id="medicine_stock" class="card-text " style="margin-top: auto; float:left;">${res[2]}</p>
                                </div>
                            </div>
                        </div>`)
                })
            })
        },
        //Create sale order for prescribe medicines from pharmacy dashboard
        create_sale_order_pharmacy: function (ev) {
            var arg = $(ev.target).data('order_id');
            rpc.query({
                model: 'hospital.outpatient',
                method: 'create_medicine_sale_order',
                args:[arg],
            }).then(function () {

            })
        },
        //Fetch vaccine data while clicking Vaccine button.
        fetch_vaccine_data: function () {
            var self = this;
            rpc.query({
                model: 'product.template',
                method: 'action_get_vaccine_data',
                args: [],
            }).then(function (result) {
                self.$('#content_div').html(``);
                self.$('#content_div').html(`
                    <h2 style="margin-top:2rem;">Vaccines</h2>
                    <div class="row medicines" id="med_items" style="height:600px; margin-left:2rem; width: 52rem; overflow-y: scroll; ">
                    </div>`);
                result.medicine.forEach(res => {
                    self.$('#med_items').append(`
                        <div class="card" style="width: 11rem; height: 17rem;margin-top: 2rem;margin-right: 2rem;">
                            <img style="width:auto; height:99px;margin-top: 11px; display: grid;justify-content:center;" class="card-img-top" src="data:image/png;base64,${res[3]}">
                            <div class="card-body" style="margin-top: 10px;">
                                <h3 id="medicine_name" class="card-title">${res[0]}</h3>
                                <div style="float:left;width:100%;">
                                    <span style="float:left;">Price:</span>
                                    <p id="medicine_price" class="card-text">${res[1]}</p>
                                </div>
                                <div style="float:left;width:100%;">
                                    <span style="float:left;">Stock:</span>
                                    <p id="medicine_stock" class="card-text">${res[2]}</p>
                                </div>
                            </div>
                        </div>`)
                })
            })
        },
        //Method for emptying the data
        clear_data: function () {
            var self = this;
            self.$('#patient_search').val('');
            self.$('#main_div').html(``);
            self.$('#content_div').html(``);
            self.$('#medical_list').html('');
            self.$('#hist_head').html('')
            self.$('#patient-title').html('')
            self.$('#patient-code').html('')
            self.$('#patient-gender').html('')
            self.$('#patient-blood').html('')
            self.$('#patient-image').attr('src', 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png');
        },
        //Create sale order for patient prescription
        createSaleOrder: function() {
            var self = this
            let data_table = self.$('#history');
            var data ={};
            data['op'] = self.$('#op_code_history').text();
            data['products']= [];
            self.$('#medicine_items tr').each(function (index, row) {
                let cols = $(row).find('td');
                data['products'].push({
                    prod: $(cols[5]).text(),
                    qty: $(cols[4]).text() || 0,
                });
            });
            rpc.query({
                model: 'hospital.pharmacy',
                method: 'create_sale_order',
                kwargs: data
            }).then(function (result) {
                self.$('#saleorder').hide();
            })
        },
        //While clicking op row details of that op will display.
        click_op_row: function (ev) {
            var arg = $(ev.target).data('op_id');
            var self = this;
            rpc.query({
                model: 'hospital.outpatient',
                method: 'action_row_click_data',
                args: [arg],
            }).then(function (result) {
                self.$('#content_div').html(`<table style="margin-top:30px; width:50%;">
                    <tr style="vertical-align:top">
                        <td><h3 id="op_code_history"/></td>
                        <td><h3>-</h3></td>
                        <td><h3 id="op_name_history"/></td>
                    </tr>
                    <tr style="vertical-align:top">
                        <td>OP Date</td>
                        <td>:</td>
                        <td id="op_date_history"/>
                    </tr>
                    <tr style="vertical-align:top">
                        <td>Slot</td>
                        <td>:</td>
                        <td id="op_ticket_history"/>
                    </tr>
                    <tr style="vertical-align:top">
                        <td>Doctor</td>
                        <td>:</td>
                        <td id="op_doctor_history"/>
                    </tr>
                    <tr style="vertical-align:top">
                        <td>Reason</td>
                        <td>:</td>
                        <td id="op_reason_history"/>
                    </tr>
                    </table>
                    <div style="overflow-x:auto">
                        <table class="medicine_table table striped">
                            <thead>
                                <tr>
                                    <th>Medicine</th>
                                    <th>Intakes</th>
                                    <th>Time</th>
                                    <th>Note</th>
                                    <th>Quantity</th>
                                </tr>
                            </thead>
                                <tbody id="medicine_items"></tbody>
                                <tbody class="add_med" id="add_med"</tbody>
                        </table>
                    </div>`)
                self.$('#op_code_history').text(result.op_data[0])
                self.$('#op_id_history').text(result.op_data[1] || '')
                self.$('#op_name_history').text(result.op_data[2] || '')
                self.$('#op_date_history').text(result.op_data[3] || '')
                self.$('#op_ticket_history').text(result.op_data[4] || '')
                self.$('#op_reason_history').text(result.op_data[5] || '')
                self.$('#op_doctor_history').text(result.op_data[6] || '')
                self.$('#medicine_items').html('');
                self.$('#add_med').html('');
                result.medicines.forEach(res => {
                    self.$('#medicine_items').append(`
                        <tr>
                            <td>${res[0]}</td>
                            <td>${res[1]}</td>
                            <td>${res[2] ? res[2].toUpperCase() : ''}</td>
                            <td>${res[3] ? res[3].toUpperCase() : ''}</td>
                            <td>${res[4]}</td>
                            <td style="display: none">${res[5]}</td>
                        </tr>
                    `);
                })
                if (!result.op_data[7]) {
                self.$('#add_med').append(`
                    <button class="btn btn-primary saleorder" id="saleorder" data-order=${result.op_data[0][0]}>
                        Create Sale Order
                    </button>
                `);
            } else {
                // If sale is already created, hide the button
                self.$('#saleorder').hide();
            }  })
        },
    })
    core.action_registry.add('pharmacy_dashboard_tags', PharmacyDashboard);
    return PharmacyDashboard;
})
