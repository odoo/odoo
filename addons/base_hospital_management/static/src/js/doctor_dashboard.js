odoo.define('base_hospital_management.doctor_dashboard_action', function (require){
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var DoctorDashboard = AbstractAction.extend({
        template: 'DoctorDashboard',
        init: function(parent, context) {
           this._super(parent, context);
        },
        //Events
        events :{
            'click .patient_search': 'fetch_patient_data',
            'click #patient': 'list_patient_data',
            'click #consultation' : 'fetch_consultation',
            'click #shift' : 'fetch_allocation_lines',
            'click #scheduled_activity':'fetch_doctors_schedule',
            'click #cancel_slot':'action_slot_cancel',
            'click #inpatient':'action_list_inpatient',
            'change #filter': '_onChangeSelection',
            'click .inpatient_row': 'fetch_inpatientRow',
            'click .listpatientdata': 'fetch_patientRow',
            'click .op-consultation': 'create_op_consultation',
            'click .search': 'search_patient_from_list',
            'click .view_slot':'view_doctors_schedule',
            'click .outpatient_row': 'view_outpatient',
            'click .booking_item': 'fetch_bookingItem'
        },
        start: function() {
            this.set("title", 'Dashboard');
            return this._super().then(function() {})
        },
        refresh: function(){
            const btns = $('.n_active')
            if (btns.length != 0){console.log(btns), btns.click()}
        },
        listPatient:[],
        //Function for feting patient data
        list_patient_data: function(){
        if(this.$('#welcome')){
            this.$('#welcome').remove()
            }
            var self = this;
            rpc.query({
                model: 'res.partner',
                method:'fetch_patient_data',
                args: [[['patient_seq', '!=', ['New','Employee']]]]
            }).then(function (result){
                if (self.$('.n_active')[0]){
                    self.$('.n_active')[0].classList.remove('n_active');
                }
                self.$('.patient_data')[0].classList.add('n_active');
                self.$('.r_AppntBtn').html('');
                self.listPatient = result;
                self.$('#main-view').html(`<div class="row">
                                <div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                                    <input class="form-control me-2 search" id="patient_search_pad" style="width:275px;"
                                           type="search"
                                           placeholder="Search" aria-label="Search"/>
                                    <button class="btn btn-outline-success search">Search</button>
                                </div>
                            </div>
                       <div class="row o_patientList">
                       <table class="table table-hover p_list">
                            <thead>
                                <tr>
                                    <th class="text-center">Sequence</th>
                                    <th class="text-center">Name</th>
                                    <th class="text-center">Gender</th>
                                    <th class="text-center">Date Of Birth</th></tr>
                            </thead>
                            <tbody id="patientlist"/>
                       </table></div>`)
                 var count=0;
                 result.forEach(element => {
                    var gender = (element.gender ? element.gender : '');
                    var date_of_birth = (element.date_of_birth ? element.date_of_birth : '');
                    self.$('#patientlist').append(`<tr class="listpatientdata"
                    data-index=${count}>
                                <td class="text-center"
                                data-index=${count}>${element.patient_seq
                                || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.name || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${gender || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${date_of_birth || ''}</td>
                            </tr>`)
                    count += 1;
                })
            })
        },
        //Method for returning the details of a patient
        fetch_patientRow: function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.listPatient[record_id];
            rpc.query({
                model: 'res.partner',
                method: 'fetch_view_id',
                args: [[['patient_seq', '!=', ['New','Employee']]]]
            }).then(function (result){
                    self.do_action({
                    name: _t("Patient Details"),
                    type: 'ir.actions.act_window',
                    res_model: 'res.partner',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[result, 'form']],
                    target: 'new',
                    })
               });
        },
        //Method for searching for a patient
        search_patient_from_list: function(){
            const btns = this.$('.n_active');
            if (btns.length != 0){
                if(btns[0].id === 'patient'){
                var search_key = this.$('#patient_search_pad').val()
                var self = this;
                rpc.query({
                    model: 'res.partner',
                    method: 'search_read',
                    kwargs: {domain: ['|','|',
                            ['date_of_birth', 'ilike', search_key],
                            ['patient_seq', 'ilike', search_key],
                            ['name', 'ilike', search_key]]},
                }).then(function (result){
                    self.listPatient = result;
                    self.$('#patientlist').html('');
                    var count = 0;
                    result.forEach(element => {
                        self.$('#patientlist').append(`
                            <tr class="listpatientdata" data-index=${count}>
                                <td class="text-center"
                                data-index=${count}>${element.patient_seq || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.name || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.gender || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.date_of_birth || ''}</td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
            else if(btns[0].id === 'inpatient'){
                var search_key = this.$('#inpatient_search').val()
                var self = this;
                rpc.query({
                    model: 'hospital.inpatient',
                    method: 'fetch_inpatient',
                    args: [false, search_key]
                }).then(function (result){
                    self.InPatientData = result;
                    self.$('#inpatient_list').html('');
                    var count = 0;
                    result.forEach(element => {
                        self.$('#inpatient_list').append(`
                            <tr class="inpatient_row" data-index=${count}>
                                <td class="text-center"
                                data-index=${count}>${element.name || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.patient_id[1] || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.type_admission || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.attending_doctor_id[1] || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.hosp_date || ''}</td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
            else if(btns[0].id === 'consultation'){
                var search_key = this.$('#outpatient_search').val()
                var self = this;
                rpc.query({
                    model: 'hospital.outpatient',
                    method: 'search_read',
                    kwargs: {domain: ['|','|','|','|',
                            ['slot', 'ilike', search_key],
                            ['op_reference', 'ilike', search_key],
                            ['patient_id.name', 'ilike', search_key],
                            ['op_date', 'ilike', search_key],
                            ['state', 'ilike', search_key]]},
                }).then(function (result){
                    self.outpatientList = result;
                    self.$('#outpatient_list').html('');
                    var count = 0;
                    result.forEach(element => {
                        self.$('#outpatient_list').append(`
                            <tr class="outpatient_row" data-index=${count}>
                                <td class="text-center"
                                data-index=${count}>${element.display_name || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.patient_id[1] || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.doctor_id[1] || ''}</td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
            }
        },
        //Method for fetching a booking item
        fetch_bookingItem : function(ev){
            var self = this;
            var record_id = parseInt(self.$(ev.target).data('index'))
            var record  = self.bookingData[record_id];
            this.do_action({
                    name: _t("Patient Booking"),
                    type: 'ir.actions.act_window',
                    res_model: 'patient.booking',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    })
        },
        //Method fo fetching patient data
        fetch_patient_data: function() {
        var self = this;
        if(self.$('#welcome')){self.$('#welcome').remove()}
            rpc.query({
                model: 'res.partner',
                method: 'action_get_patient_data',
                args: [self.$('#patient_search').val()],
            }).then(function (result){
                self.$('#patient-name').text(`${result.name} - (${result.unique})`);
                self.$('#patient-age').text(result.dob || '');
                self.$('#patient-blood').text(result.blood_group || '');
                self.$('#patient-blood').text(result.blood_group || '');
                self.$('#patient-gender').text(result.gender || '');
                self.$('#patient-status').text(result.status || '');
                self.$('#patient-phone').text(result.phone || '');
                self.$('#patient-email').text(result.email || '');
                self.$('#patient-image').attr('src', 'data:image/png;base64, '+result.image_1920);
            })
        },
        inpatientList: [],
        //method for generating list of inpatients
        action_list_inpatient: function() {
        var self = this;
        if(self.$('#welcome')){self.$('#welcome').remove()}
        self.$('#view_secondary').html('');
            if (self.$('.n_active')[0]){self.$('.n_active')[0].classList.remove('n_active');}
            self.$('.inpatient_button')[0].classList.add('n_active');
             rpc.query({
                model: 'hospital.inpatient',
                method: 'hospital_inpatient_list',
            }).then(function (result){
               self.inpatientList = result;
               self.$('#main-view').html(
                `<div class="row">
                                <div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                                    <input class="form-control me-2" id="inpatient_search" style="width:275px;"
                                           type="search"
                                           placeholder="Search" aria-label="Search"/>
                                    <button class="btn btn-outline-success search">Search</button>
                                </div>
                            </div>
                            <div class="row o_patientList">
                            <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Sequence</th>
                                    <th>Patient</th>
                                    <th>Admission</th>
                                    <th>Attending Doctor</th>
                                    <th>Hospitalization Date</th>
                                </tr>
                            </thead>
                            <tbody id="inpatient_list"/></table></div>`)
                var count = 0;
                result['record'].forEach(element => {
                self.$('#inpatient_list').append(`<tr class='inpatient_row'
                     data-index=${count}><td data-index=${count} value=${element['name'] || ''}>
                ${element['name']}</td>
                <td data-index=${count} value=${element['patient_id'] || ''}>
                ${element['patient_id']}</td>
                <td data-index=${count} value=${element['admission_type'].toUpperCase() || ''}>
                ${element['admission_type']}</td>
                <td data-index=${count} value=${element['attending_doctor_id'] || ''
                }>
                ${element['attending_doctor_id'] || ''}</td>
                <td data-index=${count} value=${element['hosp_date'] || ''}>
                ${element['hosp_date']}</td>
                 </tr>`)
                    count += 1;
                })
            })
        },
        //Method for fetching a particular patient
        fetch_inpatientRow: function(ev){
            var self = this;
            var record_id = parseInt(self.$(ev.target).data('index'))
            var record  = self.inpatientList.record[record_id];
            this.do_action({
                name: _t("Inpatient Details"),
                type: 'ir.actions.act_window',
                res_model: 'hospital.inpatient',
                res_id: record.id,
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                })
        },
        scheduleList: [],
        //Fetch doctor's schedule
        fetch_doctors_schedule: function() {
         if (this.$('.n_active')[0]){this.$('.n_active')[0].classList.remove('n_active');}
            this.$('.scheduled_activity')[0].classList.add('n_active');
         var self = this;
         if(self.$('#welcome')){self.$('#welcome').remove()}
         rpc.query({
                model: 'inpatient.surgery',
                method: 'get_doctor_slot',
                args: [],
            }).then(function (line){
            self.scheduleList = line;
            self.$('#main-view').html(`
            </br>
            </br><table class="table table-striped">
                <thead>
                <tr>
                <th scope="col">
                    Planned Date
                </th>
                <th scope="col">
                    Patient ID
                </th>
                <th scope="col">
                    Surgery
                </th>
                <th>
                    State
                </th>
                </tr>
                </thead>
                <tbody class='doctors_slot' id="doctors_slot">
                </tbody>
                </table>`)
                var count = 0;
                line['record'].forEach(element => {
                self.$('#doctors_slot').append(`<tr
                class='view_slot'data-state=${element['state'] || ''} data-index=${count}>
                <td value=${element['planned_date']}
                data-index=${count}>${element['planned_date'] || ''}</td>
                <td value=${element['patient_id']}
                data-index=${count}>${element['patient_id'] || ''}</td>
                <td value=${element['Surgery Details']}
                data-index=${count}>${element['surgery_name'] || ''}</td>
                <td value=${element['State']}
                data-index=${count}>${element['state'] || ''}</td>
                <input type="hidden" value=${element['id']}
                id='slot_id'>${element['id'] || ''}</input>
                </tr>`);
                count += 1;
                })
            })
        },
        //Method for viewing doctor's schedule
        view_doctors_schedule : function(ev) {
            var self = this;
            var record_id = parseInt(self.$(ev.target).data('index'))
            var record  = self.scheduleList.record[record_id];
            this.do_action({
                    name: _t("Schedules"),
                    type: 'ir.actions.act_window',
                    res_model: 'inpatient.surgery',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    })
        },
        outpatientList:[],
        //Method for fetching consultation details
        fetch_consultation: function(){
            var self = this;
            if(self.$('#welcome')){self.$('#welcome').remove()}
            if (self.$('.n_active')[0]){self.$('.n_active')[0].classList.remove('n_active');}
                self.$('.outpatient_button')[0].classList.add('n_active');
                var self = this;
                 rpc.query({
                    model: 'hospital.outpatient',
                    method: 'search_read',
                }).then(function (result){
                   self.outpatientList = result;
                    $('#main-view').html(
                    `<div class="row">
                                    <div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                                        <input class="form-control me-2" id="outpatient_search" style="width:275px;"
                                               type="search"
                                               placeholder="Search" aria-label="Search"/>
                                        <button class="btn btn-outline-success search">Search</button>
                                        <button class="btn btn-outline-success op-consultation" style="margin-left:10px;">Create</button>
                                    </div>
                                </div>
                                <div class="row o_outpatientList">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th class="text-center">Sequence</th>
                                                <th class="text-center">Patient</th>
                                                <th class="text-center">Doctor</th>
                                                <th class="text-center">Date</th>
                                                <th class="text-center">Slot</th>
                                                <th class="text-center">State</th>
                                            </tr>
                                        </thead>
                                        <tbody id="outpatient_list"/>
                                    </table>
                                </div>`)
                     var count = 0;
                     result.forEach(element => {
                         self.$('#outpatient_list').append(`<tr class="outpatient_row" data-index=${count}>
                                    <td class="text-center"
                                    data-index=${count}>${element.display_name || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.patient_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.doctor_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.op_date || ''}</td>
                                     <td class="text-center"
                                    data-index=${count}>${element.slot || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.state.toUpperCase() || ''}</td>
                                </tr>`)
                        count += 1;
                    })
                })
            },
        //Method for viewing outpatients
        view_outpatient:function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.outpatientList[record_id];
            this.do_action({
                name: _t("Inpatient Details"),
                type: 'ir.actions.act_window',
                res_model: 'hospital.outpatient',
                res_id: record.id,
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                })
        },
        //Method for creating OP consultation
        create_op_consultation: function(){
            this.do_action({
                name: _t("Consultation"),
                type: 'ir.actions.act_window',
                res_model: 'hospital.outpatient',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
            });
            this.fetch_consultation();
        },
        //Method for fetching allocated hours.
        fetch_allocation_lines: function() {
            var self = this;
            if(self.$('#welcome')){self.$('#welcome').remove()}
            if (self.$('.n_active')[0]){self.$('.n_active')[0].classList.remove('n_active');}
                self.$('.shift')[0].classList.add('n_active');
            rpc.query({
                    model: 'doctor.allocation',
                    method: 'get_allocation_lines',
                    args: [],
                }).then(function (result){
                self.$('#main-view').html(`<table class="table table-striped">
                        <thead>
                        <tr>
                            <th scope="col">
                                Name
                            </th>
                            <th scope="col">
                                Date
                            </th>
                            <th scope="col">
                                Patient Type
                            </th>
                            <th scope="col">
                                Limit
                            </th>
                            <th scope="col">
                                Patient Count
                            </th>
                        </tr>
                    </thead>
                    <tbody class='doctors_shift' id="doctors_shift">
                    </tbody>
                    </table>`)
                var count = 0;
                result['record'].forEach(element => {
                $('#doctors_shift').append(`<tr><td value=${element['name'] || ''}>
                ${element['name'] || ''}</td>
                <td value=${element['date'] || ''}>
                ${element['date'] || ''}</td>
                <td value=${element['patient_type'] || ''}>
                ${element['patient_type'].toUpperCase() || ''}</td>
                 <td value=${element['patient_limit'] || 0}>
                ${element['patient_limit'] || ''}</td>
                 <td value=${element['patient_count'] || 0}>
                 ${element['patient_count'] || 0}</td></tr>`);
                count += 1;
            })
            })
        }
    })
    core.action_registry.add('doctor_dashboard_tags', DoctorDashboard);
    return DoctorDashboard;
})
