odoo.define('base_hospital_management.lab_dashboard_action', function (require){
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var uom_lst= [];
    var LabDashBoard = AbstractAction.extend({
        template: 'LabDashboard',
        init: function(parent, context) {
           this._super(parent, context);
        },
        //Events
        events :{
            'click #btn_patient_search': '_Search',
            'click .test_item': '_fetchTestData',
            'click .all_test_item': 'fetch_all_test_data',
            'click .removeTest': 'removeTest',
            'click #confirm-test': 'confirmLabTest',
            'click #create': 'Create',
            'click #start-test': 'startLabTest',
            'click #test-result-edit': 'testResultEdit',
            'change #result-attachment': '_onChangeFile',
            'change #recurring': '_onChangeRecurring',
            'change #vaccine-patient-name': '_onChangeRecurring',
             'click #create-vaccination': '_createVaccination',
            'click #update-result': 'testResultUpdate',
            'click #end-test': 'endLabTest',
            'click #invoice-test': 'invoiceLabTest',
            'click #print-test-invoice': 'printInvoiceLabTest',
            'click #print-test-sale': 'printSaleLabTest',
            'click #all-test': '_allLabTest',
            'click #test-create': '_loadTestData',
            'click #published-test': '_loadPublished',
            'click #vaccination': '_vaccination',
            'click .vaccine-data': 'fetchVaccineData',
        },
        listVaccine:[],
        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self._loadTestData();
            })
        },
        state: '',
        //Search function
        _Search: function() {
            var self = this
            if (self.state == 'patient.lab.test'){
                var search_key = $('#patient_search').val();
                rpc.query({
                model: 'patient.lab.test',
                method: 'search_read',
                kwargs: {domain: ['|','|','|',['test_id.name', 'ilike', search_key],
                                            ['name', 'ilike', search_key],
                                            ['patient_id.patient_seq', 'ilike', search_key],
                                            ['patient_id.name', 'ilike', search_key]]},
                }).then(function (result){
                    self.testData = result;
                    var count = 0;
                    self.$('#main-view').html(
                    `<table class="table table-hover"><thead><tr><th>Sequence</th>
                     <th class="text-center">Patient</th><th class="text-center">Date</th><th class="text-center">Price</th><th class="text-end">State</th></tr>
                     </thead><tbody id="record_list"/></table>`)
                     result.reverse().forEach(element => {
                        self.$('#record_list').append(`
                            <tr class="all_test_item" data-index=${count || ''}>
                                <td class="text-start"
                                data-index=${count}>${element.test_id.name || ''}</td>
                                <td class="text-start"
                                data-index=${count}>${element.patient_id[1] || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.date || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.total_price || 0}</td>
                                <td class="text-end"
                                data-index=${count}>${element.state.toUpperCase() || ''}</td>
                                <td class="text-end" data-index="${count}">
                              ${element.attachment_id ? `
                                <a href="/web/content/${element.attachment_id}?download=true&amp;access_token=" class='btn btn-outline-primary fa fa-download'/>
                              ` : ''}
                            </td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
            else if (self.state == 'hospital.vaccination'){
                var search_key = self.$('#patient_search').val();
                rpc.query({
                model: 'hospital.vaccination',
                method: 'fetch_vaccination_data',
                kwargs: {domain: ['|','|','|',['vaccine_product_id.name', 'ilike', search_key],
                                            ['name', 'ilike', search_key],
                                            ['patient_id.patient_seq', 'ilike', search_key],
                                            ['patient_id.name', 'ilike', search_key]]},
            }).then(function (result){
                var count = 1;
                self.$('#main-view').html(
                `<table class="table table-hover"><thead><tr id='view-vaccination'><th>Sequence</th>
                 <th>Patient</th><th>Vaccine</th><th class="text-end">Price</th><th class="text-end">Certificate</th></tr>
                 </thead><tbody id="record_list"/></table>`)
                 result.forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="vaccine-data" data-index=${count || ''}>
                            <td class="text-start" data-index=${count}>${element.name || ''}</td>
                            <td class="text-start" data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-start" data-index=${count}>${element.vaccine_product_id || ''}</td>
                            <td class="text-end" data-index=${count}>${element.vaccine_price || ''}</td>
                            <td class="text-end" data-index="${count}">
                              ${element.attachment_id ? `
                                <a href="/web/content/${element.attachment_id}?download=true&amp;access_token=" class='btn btn-outline-primary fa fa-download'/>
                              ` : ''}
                            </td>
                        </tr>
                    `)
                    count += 1;
                })
            })
            }
            else if (self.state == 'lab.test.result'){
                var search_key = self.$('#patient_search').val();
                rpc.query({
                model: 'lab.test.result',
                method: 'print_test_results',
                kwargs: {domain: ['|','|',
                                            ['test_id.name', 'ilike', search_key],
                                            ['parent_id.patient_id.patient_seq', 'ilike', search_key],
                                            ['parent_id.patient_id.name', 'ilike', search_key]]},
            }).then(function (result){
                var count = 1;
                self.$('#main-view').html(
                `<table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Sequence</th>
                            <th>Patient</th>
                            <th>Test</th>
                            <th style='text-align:right'>Result</th>
                        </tr>
                    </thead>
                 <tbody id="record_list"/>
                </table>`)
                 result.reverse().forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="published_item" data-index=${count || ''}>
                            <td class="text-start" data-index=${count}>${element.parent_id || ''}</td>
                            <td class="text-start" data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-start" data-index=${count}>${element.test_id || ''}</td>
                             <td class="text-end" data-index="${count}">
                              ${element.attachment_id ? `
                                <a href="/web/content/${element.attachment_id}?download=true&amp;access_token=" class='btn btn-outline-primary fa fa-download'/>
                              ` : ''}
                            </td>
                        </tr>
                    `)
                    count += 1;
                })
            })
            }
            else if (self.state == 'lab.test.line'){
                var self = this;
                var search_key = self.$('#patient_search').val();
                self.state = 'lab.test.line'
                 rpc.query({
                    model: 'lab.test.line',
                    method: 'search_read',
                    kwargs: {domain: ['|','|',['name', 'ilike', search_key],
                                            ['patient_id.patient_seq', 'ilike', search_key],
                                            ['patient_id.name', 'ilike', search_key],
                                            ['state', '=', 'draft']]},
                }).then(function (result){
                    self.testData = result;
                    var count = 0;
                    self.$('#main-view').html(
                    `<table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Sequence</th>
                                <th class="text-start">Patient</th>
                                <th class="text-center">Doctor</th>
                                <th class="text-center">Type</th>
                                <th class="text-end">Date</th>
                            </tr>
                         </thead>
                     <tbody id="record_list"/>
                     </table>`)
                    result.reverse().forEach(element => {
                        self.$('#record_list').append(`
                            <tr class="test_item" data-index=${count || ''}>
                                <td class="text-start" data-index=${count}>${element.name || ''}</td>
                                <td class="text-center" data-index=${count}>${element.patient_id[1] || ''}</td>
                                <td class="text-center" data-index=${count}>${element.doctor_id[1] || ''}</td>
                                <td class="text-center" data-index=${count}>${element.patient_type.toUpperCase() || ''}</td>
                                <td class="text-end" data-index=${count}>${element.date || ''}</td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
        },
         //Method for returning the details of a vaccination
        fetchVaccineData: function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.listVaccine[record_id];
            rpc.query({
                model: 'hospital.vaccination',
                method: 'fetch_vaccination_data',
                kwargs: {domain: []},
            }).then(function (result){
                    self.do_action({
                    name: _t("Vaccinations"),
                    type: 'ir.actions.act_window',
                    res_model: 'hospital.vaccination',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[result['view_id'], 'form']],
                    target: 'new',
                    })
               });
        },
        //Method for fetching all lab tests
        _allLabTest: function() {
            var self = this
            self.state = 'patient.lab.test'
            self.$('#create-button').html('')
             rpc.query({
                model: 'patient.lab.test',
                method: 'search_read',
            }).then(function (result){
                self.$('#form-view').attr('hidden', 'true');
                self.testData = result;
                var count = 0;
                self.$('#main-view').html(
                `<table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Sequence</th>
                            <th class="text-center">Patient</th>
                            <th class="text-center">Date</th>
                            <th class="text-center">Price</th>
                            <th class="text-end">State</th>
                        </tr>
                    </thead>
                    <tbody id="record_list"/>
                </table>`)
                 result.reverse().forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="all_test_item" data-index=${count || ''}>
                            <td class="text-start" data-index=${count}>${element.test_id[1] || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-center" data-index=${count}>${element.date || ''}</td>
                            <td class="text-center" data-index=${count}>${element.total_price || ''}</td>
                            <td class="text-end" data-index=${count}>${element.state.toUpperCase() || ''}</td>
                        </tr>
                    `)
                    count += 1;
                })
            })
        },
        //Method for creating vaccinations
        Create: function(){
            var self = this
            if (self.state == 'hospital.vaccination')
            {
              this.do_action({
                name: _t("Vaccination"),
                type: 'ir.actions.act_window',
                res_model: 'hospital.vaccination',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
             });
            }
            else{
                this.do_action({
                    name: _t("Lab Test"),
                    type: 'ir.actions.act_window',
                    res_model: 'lab.test.line',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                 }, {
                on_close: function () {
                     self._loadTestData();
                }});
            }
        },
        //Method for recurrent vaccination
        _onChangeRecurring: function(){
            if(self.$('#recurring').is(':checked')){
                self.$('#data-recurring').show()
                var patient_id = parseInt(self.$('#vaccine-patient-name').val())
                if (patient_id){
                    rpc.query({
                        model: 'hospital.vaccination',
                        method: 'search_read',
                        kwargs: {
                            fields: ['id', 'name'],
                            domain: [['patient_id', '=', patient_id],
                            ['recurring_vaccine', '=', true]]
                        }
                        }).then(function (result){
                            self.$('#old-data').html('')
                            result.forEach(element => {
                                self.$('#old-data').append(`
                                    <option value="${element.id}">${element.name || ''}</option>
                                `)
                            })

                        });
                    }
            }else{
                self.$('#data-recurring').hide()
            }
        },
        //Method for creating draft tests
        CreateDraftTest: function(){
            var self = this;
            var patient_id = self.$('#test-patient-name').val();
            var patient_type = self.$('#test-patient-type').val();
            var doctor_id = self.$('#test-doctor').val();
            var date = self.$('#test-date').val();
            var value = {
                patient_id : parseInt(patient_id),
                doctor_id : parseInt(doctor_id),
                patient_type : patient_type
            }
            this._rpc({
                model: self.state,
                method: 'create',
                args: [value],
            })
            .then(function (result) {
               self.$('#test-modal-close').click()
               self._loadTestData()
            })
        },
        //Method for creating vaccinations
        _createVaccination: function(){
            var self = this;
            var data = {
                patient_id :parseInt(self.$('#vaccine-patient-name').val()),
                dose : parseFloat(self.$('#vaccine-dose').val()),
                vaccine_product_id : parseInt(self.$('#vaccine-name').val()),
            }
            if(self.$('#recurring').is(':checked')){
                data['recurring_vaccine'] = true
                data['parent_id'] = parseInt(self.$('#old-data'))
            }
            this._rpc({
                model: self.state,
                method: 'create',
                args: [data],
            })
            .then(function (result) {
               self.$('.btn-close').click()
               self._vaccination()
            })
        },
        testData: [],
        //Method for getting all test data
        fetch_all_test_data: function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            self.load_all_test_data(record_id)
        },
        //Method for loading all test data
        load_all_test_data: function(record_id){
            var self = this;
            var record  = self.testData[record_id];
            rpc.query({
                model: 'patient.lab.test',
                method: 'action_get_patient_data',
                args: [record.id],
            }).then(function (result){
                self.load_data(result)
                self.$('#action-table').html(`
                    <h4>Tests</h4>
                    <ul id="tests"></ul>
                    <h4>Medicines</h4>
                    <table class="table"><thead><tr><th>Sl</th><th>Medicine</th><th>Quantity</th>
                    </tr></thead><tbody id="medicine-list">
                    </tbody></table>
                `)
                result['test_data'].forEach(element => {
                    self.$('#tests').append(`<li>${element.name}</li>`)
                })
                if(result.result_ids.length > 0){
                    self.$('#action-table').append(`
                        <h4>Results</h4>
                        <table class="table table-hover"><thead><tr><th>Name</th><th>Result</th><th>Normal</th>
                        <th>Unit</th><th>Cost</th><th>State</th></tr></thead>
                        <tbody id="result-list"></tbody></table>
                    `)
                    result['result_ids'].forEach(element => {
                    self.$('#result-list').append(`
                        <tr data-id=${element.id} data-index=${record_id} id='test-result-edit' data-bs-toggle="modal"
                            data-bs-target="#test-result-edit-modal">
                            <td data-id=${element.id} data-index=${record_id}>${element.name || ''}</td>
                            <td data-id=${element.id} data-index=${record_id}>${element.result || ''}</td>
                            <td data-id=${element.id} data-index=${record_id}>${element.normal || ''}</td>
                            <td data-id=${element.id} data-index=${record_id}>${element.uom_id[1] || ''}</td>
                            <td data-id=${element.id} data-index=${record_id}>${element.cost || ''}</td>
                            <td data-id=${element.id} data-index=${record_id}>${element.state.toUpperCase() || ''}</td>
                        </tr>
                    `)
                    })
                }
                var count = 1
                result['medicine'].forEach(element => {
                    self.$('#medicine-list').append(`
                        <tr>
                           <td>${count}</td>
                           <td>${element.name}</td>
                           <td>${element.quantity}</td>
                       </tr>
                    `)
                })
                if (result.state == 'draft'){
                    self.$('#action-button').html(`
                    <button class="btn btn-primary col-md-2"
                        id="start-test" data-id=${result.id} data-index=${record_id}>Start</button>
                       `)
                }else if(result.state == 'test'){
                    self.$('#action-button').html(`
                    <button class="btn btn-primary col-md-2"
                        id="end-test" data-id=${result.id} data-index=${record_id}>End</button>
                        `)
                     if(!result.invoiced){
                        self.$('#action-button').append(`
                            <button class="btn btn-primary col-md-2"
                            id="invoice-test" data-id=${result.id} data-index=${record_id}>Create Invoice</button>
                        `)
                    }else{
                        self.$('#action-button').append(`
                            <button class="btn btn-primary col-md-2"
                            id="print-test-invoice" data-id=${result.id} data-index=${record_id}>Print Invoice</button>
                            <button class="btn btn-primary col-md-2"
                            id="print-test-sale" data-id=${result.id} data-index=${record_id}>Print Quotation</button>
                        `)
                    }
                }else if(result.state == 'completed'){
                    self.$('#action-button').html('')
                    if(!result.invoiced){
                        self.$('#action-button').html(`
                            <button class="btn btn-primary col-md-2"
                            id="invoice-test" data-id=${result.id} data-index=${record_id}>Create Invoice</button>
                        `)
                    }else{
                        self.$('#action-button').append(`
                            <button class="btn btn-primary col-md-2"
                            id="print-test-invoice" data-id=${result.id} data-index=${record_id}>Print Invoice</button>
                            <button class="btn btn-primary col-md-2"
                            id="print-test-sale" data-id=${result.id} data-index=${record_id}>Print Quotation</button>
                        `)
                    }
                }
            })
        },
        //Method for starting the lab test
        startLabTest: function(ev){
            var self = this
            var record_id = parseInt($(ev.target).data('id'))
            var index_id = parseInt($(ev.target).data('index'))
            rpc.query({
                model: 'patient.lab.test',
                method: 'start_test',
                args: [record_id],
            }).then(function (result){
                self.load_all_test_data(index_id)
            })
        },
        //Method for ending la test
        endLabTest: function(ev){
            var self = this
            var record_id = parseInt($(ev.target).data('id'))
            var index_id = parseInt($(ev.target).data('index'))
            rpc.query({
                model: 'patient.lab.test',
                method: 'test_end',
                args: [record_id],
            }).then(function (result){
                self.load_all_test_data(index_id)
            })
        },
        //Method for invoicing lab test
        invoiceLabTest: function(ev){
            var self = this
            var record_id = parseInt($(ev.target).data('id'))
            var index_id = parseInt($(ev.target).data('index'))
            rpc.query({
                model: 'patient.lab.test',
                method: 'create_invoice',
                args: [record_id],
            }).then(function (result){
                self.load_all_test_data(index_id)
            })
        },
        //Method for printing lab test
        printInvoiceLabTest: function(ev){
            var self = this
            var record_id = parseInt($(ev.target).data('id'))
            var index_id = parseInt($(ev.target).data('index'))
            rpc.query({
                model: 'patient.lab.test',
                method: 'search_read',
                kwargs: {
                    fields: ['invoice_id'],
                    domain: [['id', '=', record_id]]
                }
            }).then(function (result){
                if (result){
                self.do_action({
                    'type': 'ir.actions.act_url',
                    'url': `/report/pdf/account.report_invoice/${result[0].invoice_id[0]}`,
                    'target': 'new',
                     })
                }
            })
        },
        //Print lab test sale order
        printSaleLabTest :function(ev){
            var self = this
            var record_id = parseInt($(ev.target).data('id'))
            var index_id = parseInt($(ev.target).data('index'))
            rpc.query({
                model: 'patient.lab.test',
                method: 'search_read',
                kwargs: {
                    fields: ['order'],
                    domain: [['id', '=', record_id]]
                }
            }).then(function (result){
                if (result){
                self.do_action({
                    'type': 'ir.actions.act_url',
                    'url': `/report/pdf/sale.report_saleorder/${result[0].order}`,
                    'target': 'new',
                     })
                }
            })
        },
        //Method to fetch uom
        fetch_uom: function () {
                var self = this;
                return rpc.query({
                    model: 'uom.uom',
                    method: 'search_read',
                    args: [''],
                }).then(function (result) {
                    self.uom_lst = result;
                    return result;
                });
            },
        //Method to update the test result
        testResultEdit: function (ev) {
            var self = this;
            var record_id = parseInt($(ev.target).data('id'));
            var index_id = parseInt($(ev.target).data('index'));
            self.fetch_uom().then(function () {
                self.$('.select_uom').html('');
                if (self.uom_lst) {
                    self.uom_lst.forEach(element => {
                        self.$('.select_uom').append(`
                            <option value="${element['id']}">${element.name}</option>
                        `);
                    });
                }
                rpc.query({
                    model: 'lab.test.result',
                    method: 'search_read',
                    kwargs: {
                        fields: ['display_name', 'id', 'normal', 'result', 'uom_id', 'parent_id'],
                        domain: [['id', '=', record_id]]
                    }
                }).then(function (result) {
                    self.$('#resultModalLabel').text(result[0].display_name || '');
                    self.$('#normal-range').val(result[0].normal || '');
                    self.$('#result-unit').val(result[0].uom_id || '');
                    self.$('#result-result').val(result[0].result || '');
                    self.$('#result-id').val(result[0].id || '');
                    self.$('#result-index').val(parseInt(index_id, 10).toString());
                });
            });
        },
        //Method for changing the attached file
        _onChangeFile: function (ev) {
            const element = $(ev.target);
            var files = element[0].files[0]
            const reader = new FileReader();
                reader.onloadend = () => {
                    element.attr('data-file', reader.result.split(',')[1])
                };
                reader.readAsDataURL(files);
        },
        //Method for updating the rest result
        testResultUpdate : function(ev){
            var self = this;
            var result_id = parseInt(this.$('#result-id').val())
            var normal_range = this.$('#normal-range').val()
            var index_id = parseInt(this.$('#result-index').val())
            var result_unit = this.$('#result-unit').val()
            var result_result = this.$('#result-result').val()
            var result_attachment = this.$('#result-attachment').data('file')
            var data = {
                'result': result_result,
                'normal': normal_range,
                'uom_id': result_unit,
                'attachment': result_attachment
            }
            rpc.query({
                model: 'lab.test.result',
                method: 'write',
                args: [[result_id], data]
            }).then(function (result){
                self.load_all_test_data(index_id)
                self.$('#modal-close').click()
            })
        },
        //Method for getting the lab test data
        _loadTestData : function(){
            var self = this;
            self.state = 'lab.test.line'
             rpc.query({
                model: 'lab.test.line',
                method: 'search_read',
                kwargs: {domain: [['state', '=', 'draft']]},
            }).then(function (result){
             self.$('#form-view').attr('hidden', 'true');
                self.testData = result;
                var count = 0;
                self.$('#main-view').html(
                `<table class="table table-hover"><thead><tr><th>Sequence</th>
                 <th>Patient</th><th>Doctor</th><th>Type</th><th>Date</th></tr>
                 </thead><tbody id="record_list"/></table>`)
                result.reverse().forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="test_item" data-index=${count || ''}>
                            <td data-index=${count}>${element.name || ''}</td>
                            <td data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td data-index=${count}>${element.doctor_id[1] || ''}</td>
                            <td data-index=${count}>${element.patient_type.toUpperCase() || ''}</td>
                            <td data-index=${count}>${element.date || ''}</td>
                        </tr>
                    `)
                    count += 1;
                })
                if(!self.$('#create').length){
                    self.$('#create-button').append('<button class="btn btn-outline-info" id="create" style="margin-left:10px;">Create</button>')
                    }
            })
        },
        //Method for getting the data of a particular lab test
        _fetchTestData : function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.testData[record_id];
            rpc.query({
                model: 'lab.test.line',
                method: 'action_get_patient_data',
                args: [record.id],
            }).then(function (result){
                self.load_data(result)
                self.$('#action-table').html(`
                    <table class="table"><thead><tr><th>Sl</th><th>Name</th>
                    <th>Lead</th><th>Price</th></tr></thead><tbody id="test-list">
                    </tbody></table>
                `)
                self.$('#action-button').html(`
                    <button class="btn btn-primary col-md-2"
                        id="confirm-test">Confirm</button>`)
                self.$('#test-list').html('')
                var count = 0;
                result['test_data'].forEach(element =>{
                    self.$('#test-list').append(`
                        <tr>
                           <td>${count+1 || ''}</td>
                           <td>${element.name || ''}</td>
                           <td>${element.patient_lead || ''}</td>
                           <td>${element.price || ''}</td>
                           <td><i class="fa fa-times removeTest" data-index=${count}/></td>
                       </tr>
                    `)
                    count += 1
                })
            })
        },
        //Method for getting result published lab tests
        _loadPublished: function (){
            var self = this;
            self.state = 'lab.test.result'
            self.$('#create-button').html('')
            rpc.query({
                model: 'lab.test.result',
                method: 'print_test_results',
                kwargs: {domain: []},
            }).then(function (result){
                self.$('#form-view').attr('hidden', 'true');
                var count = 1;
                self.$('#main-view').html(
                `<table class="table table-hover"><thead><tr><th>Sequence</th>
                 <th>Patient</th><th>Test</th><th>Normal</th>
                 <th>Result</th>
                 <th>Unit</th>
                 <th style='text-align:right'>Attachment</th></tr>
                 </thead><tbody id="record_list"/></table>`)
                 result.reverse().forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="published_item" data-index=${count || ''}>
                            <td class="text-start" data-index=${count}>${element.parent_id || ''}</td>
                            <td class="text-start" data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-start" data-index=${count}>${element.test_id || ''}</td>
                            <td class="text-start" data-index=${count}>${element.normal || ''}</td>
                            <td class="text-start" data-index=${count}>${element.result || ''}</td>
                            <td class="text-start" data-index=${count}>${element.unit || ''}</td>
                            <td class="text-end" data-index="${count}">
                              ${element.attachment_id ? `
                                <a href="/web/content/${element.attachment_id}?download=true&amp;access_token=" class='btn btn-outline-primary fa fa-download'/>
                              ` : ''}
                            </td>
                            </tr>
                    `)
                    count += 1;
                })
            })
        },
        //Method for fetching all vaccinations
        _vaccination: function(){
            var self = this
            self.state = 'hospital.vaccination'
            if(!self.$('#create').length){
                self.$('#create-button').append('<button class="btn btn-outline-info" id="create" style="margin-left:10px;">Create</button>')
            }
            rpc.query({
                model: 'hospital.vaccination',
                method: 'fetch_vaccination_data',
                kwargs: {domain: []},
            }).then(function (result){
                self.listVaccine=result;
                self.$('#form-view').attr('hidden', 'true');
                self.testData = result;
                var count = 0;
                self.$('#main-view').html(
                `<table class="table table-hover"><thead><tr><th>Sequence</th>
                 <th>Patient</th><th>Vaccine</th><th class="text-end">Price</th><th class="text-end">Certificate</th></tr>
                 </thead><tbody id="record_list"/></table>`)
                 result.forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="vaccine-data" data-index=${count || ''}>
                            <td class="text-start" data-index=${count}>${element.name || ''}</td>
                            <td class="text-start" data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-start" data-index=${count}>${element.vaccine_product_id || ''}</td>
                            <td class="text-end" data-index=${count}>${element.vaccine_price || ''}</td>
                            <td class="text-end" data-index="${count}">
                              ${element.attachment_id ? `
                                <a href="/web/content/${element.attachment_id}?download=true&amp;access_token=" class='btn btn-outline-primary fa fa-download'/>
                              ` : ''}
                            </td>  </tr>
                    `)
                    count += 1;
                })
            })
        },
        currentData: [],
        //Method for displaying the patient data
        load_data: function(result){
            var self = this;
            self.currentData = result
            self.$('#form-view').removeAttr('hidden')
            self.$('.LabReport').removeAttr('hidden')
            self.$('#patient-name').text(`${result.name} - (${result.unique})`);
            self.$('#patient-age').text(result.dob || '');
            self.$('#patient-blood').text(result.blood_group || '');
            self.$('#patient-gender').text(result.gender || '');
            self.$('#patient-status').text(result.status || '');
            self.$('#patient-phone').text(result.phone || '');
            self.$('#patient-email').text(result.email || '');
            self.$('#patient-doctor').text(result.doctor || '');
            self.$('#patient-slot').text(result.slot || '');
            self.$('#patient-patient_type').text(result.patient_type || '');
            self.$('#patient-image').attr('src', 'data:image/png;base64, '+result.image_1920);
        },
        //Method for creating lab test
        confirmLabTest: function(ev){
            var self = this;
             rpc.query({
                model: 'lab.test.line',
                method: 'create_lab_tests',
                args: [self.currentData],
             }).then(function (result){
                self._allLabTest()
             })
        },
        //Method for removing a lab test
        removeTest: function(ev){
            var self = this
            self.currentData['test_data'].splice($(ev.target).data('index'),1);
            $(ev.target).parent().parent().css({ 'color': 'red'})
        },
    })
    core.action_registry.add('lab_dashboard_tags', LabDashBoard);
    return LabDashBoard;
})
