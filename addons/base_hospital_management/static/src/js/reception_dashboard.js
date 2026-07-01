odoo.define('base_hospital_management.reception_dashboard_action', function (require){
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var FormController = require('web.FormController');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var patient_lst = [];
    var patient_id_lst = [];
    var dr_lst = [];
    var attending_dr_lst = [];
    localStorage.setItem('patient_lst',patient_lst);
    var ReceptionDashBoard = AbstractAction.extend({
        template: 'ReceptionDashboard',
        init: function(parent, context) {
           this._super(parent, context);
        },
        //Events
        events :{
            'click .o_patient_button': 'createPatient',
            'click .patient_item': 'fetch_patient',
            'click .outpatient_item': 'fetch_outPatientItem',
            'click .inpatient_item': 'fetch_inPatientItem',
            'click .booking_item': 'fetch_bookingItem',
            'click .o_appointment_button': 'fetchAppointmentData',
            'click .patient_create': 'createPatient',
            'click .inpatient_create': 'createInPatient',
            'click .outpatient_create': 'createOutPatient',
            'click .allocation_create': 'createAllocation',
            'click #view_patient_profile': 'patientBackendView',
            'change #patient-img': 'fileCreate',
            'click .save_patient': 'savePatient',
            'change #op_date': 'fetchAllocation',
            'click .save_out_patient': 'save_out_patient_data',
            'click .save_in_patient': 'save_in_patient_data',
            'click .saveandnew_patient': 'save_and_new',
            'click .saveandnew_out_patient': 'o_save_and_new',
            'click .saveandnew_in_patient': 'i_save_and_new',
            'click .o_patient_history_button': 'fetchPatientsData',
            'click .o_out_patient_history_button': 'fetchOutPatient',
            'click .ward_create': 'createWard',
            'click .o_room_ward_button': 'fetchRoomWard',
            'click .o_outpatient_button': 'createOutPatient',
            'click .o_inpatient_button': 'createInPatient',
            'click .o_in_patient_history_button': 'fetchInPatient',
            'click .o_room_button': 'fetchRoom',
            'click .o_ward_button': 'fetchWard',
            'click .o_doctor_allocation': 'createAllocation',
            'click .search': '_Search',
            'click .select_type': 'patient_card',
            'change #sl_patient': 'fetch_patient_id',
            'change #o_patient-phone': 'fetch_patient_phone',
        },
        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            self.createPatient();
        },
        //Patient search function
        _Search: function(){
            var self=this
            const btns = self.$('.r_active')
            const apptmnt_btns = self.$('.r_active1')
            const roomward_btns = self.$('.r_active2')
            if(btns[0].id === 'patient'){
                var search_key = self.$('#patient_search').val()
                var self = this;
                rpc.query({
                    model: 'res.partner',
                    method: 'search_read',
                    kwargs: {domain: ['|','|',
                            ['date_of_birth', 'ilike', search_key],
                            ['patient_seq', 'ilike', search_key],
                            ['name', 'ilike', search_key]]},
                }).then(function (result){
                    self.patientData = result;
                    self.$('#record_list').html('');
                    var count = 0;
                    result.forEach(element => {
                        self.$('#record_list').append(`
                            <tr class="patient_item" data-index=${count}>
                                <td class="text-start" data-index=${count}>${element.patient_seq || ''}</td>
                                <td class="text-center" data-index=${count}>${element.name || ''}</td>
                                <td class="text-center" data-index=${count}>${element.gender.toUpperCase() || ''}</td>
                                <td class="text-center" data-index=${count}>${element.date_of_birth || ''}</td>
                            </tr>
                        `)
                        count += 1;
                    })
                })
            }
            else if(btns[0].id === 'booking'){
                var search_key = self.$('#booking_search').val()
                var self = this;
                rpc.query({
                    model: 'patient.booking',
                    method: 'search_read',
                    kwargs: {domain: ['|','|','|','|',
                            ['booking_reference', 'ilike', search_key],
                            ['patient_id.name', 'ilike', search_key],
                            ['patient_id.patient_seq', 'ilike', search_key],
                            ['state', 'ilike', search_key],
                            ['booking_date', 'ilike', search_key]]},
                }).then(function (result){
                   self.bookingData = result;
                   self.$('#record_list').html('');
                    var count = 0;
                    result.forEach(element => {
                        self.$('#record_list').append(`<tr class="booking_item" data-index=${count}>
                                <td class="text-start"
                                data-index=${count}>${element.booking_reference|| '' }</td>
                                <td class="text-center" data-index=${count}>${element.patient_id[1]|| ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.doctor_id[1] || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.booking_date || ''}</td>
                                <td class="text-center"
                                data-index=${count}>${element.state.toUpperCase() || ''}</td>
                            </tr>`)
                        count += 1;
                    })
                })
            }
            if (apptmnt_btns.length != 0){
                if(apptmnt_btns[0].id === 'outpatient'){
                    var search_key = $('#outpatient_search').val()
                    var self = this;
                    rpc.query({
                        model: 'hospital.outpatient',
                        method: 'search_read',
                        kwargs: {domain: ['|','|','|','|',
                                ['slot', 'ilike', search_key],
                                ['patient_id.patient_seq', 'ilike', search_key],
                                ['patient_id.name', 'ilike', search_key],
                                ['op_date', 'ilike', search_key],
                                ['state', 'ilike', search_key]]},
                    }).then(function (result){
                        self.OutPatientData = result;
                        self.$('#record_list').html('');
                        var count = 0;
                        result.forEach(element => {
                            self.$('#record_list').append(`
                                <tr class="outpatient_item" data-index=${count}>
                                    <td class="text-start"
                                    data-index=${count}>${element.display_name || ''}</td>
                                    <td class="text-start" data-index=${count}>${element.slot === 0.0 ? '' : self.floatToTime(element.slot) || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.patient_id[1]  || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.doctor_id[1]  || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.op_date  || ''}</td>
                                    <td class="text-center" data-index=${count}>${element.state.toUpperCase()|| ''}</td>
                                </tr>
                            `)
                            count += 1;
                        })
                    })
                }
                else if(apptmnt_btns[0].id === 'inpatient'){
                   var search_key = $('#inpatient_search').val()
                    var self = this;
                    rpc.query({
                        model: 'hospital.inpatient',
                        method: 'fetch_inpatient',
                        args: [false, search_key]
                    }).then(function (result){
                        self.InPatientData = result;
                        self.$('#record_list').html('');
                        var count = 0;
                        result.forEach(element => {
                            self.$('#record_list').append(`
                                <tr class="inpatient_item" data-index=${count}>
                                    <td class="text-start"
                                    data-index=${count}>${element.name||
                                    ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.patient_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.ward_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.bed_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.attending_doctor_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.hosp_date || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.discharge_date || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.state.toUpperCase() || ''}</td>
                                </tr>
                            `)
                            count += 1;
                        })
                    })
                }
                else if(apptmnt_btns[0].id === 'doctor_slot'){
                    var self = this;
                    var search_key = $('#allocation_search').val()
                    rpc.query({
                        model: 'doctor.allocation',
                        method: 'search_read',
                        kwargs: {domain: ['|','|','|',
                                ['doctor_id.name', 'ilike', search_key],
                                ['department_id', 'ilike', search_key],
                                ['date', 'ilike', search_key],
                                ['op_number', 'ilike', search_key]]},
                    }).then(function (result){
                        self.$('#record_list').html('');
                        self.doctorData = result;
                        var count = 0;
                        result.forEach(element => {
                            self.$('#record_list').append(`<tr class="allocation_item" data-index=${count}>
                                    <td class="text-start"
                                    data-index=${count}>${element.doctor_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.department_id[1] || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.date || ''}</td>
                                    <td class="text-center"
                                    data-index=${count}>${element.op_number || ''}</td></tr>`)
                            count += 1;
                        })
                    });
                }
            }
            if (roomward_btns.length != 0){
                if(roomward_btns[0].id === 'room'){
                    var search_key = $('#room_search').val()
                    var self = this;
                    rpc.query({
                    model: 'patient.room',
                    method: 'search_read',
                    kwargs: {domain: ['|','|',
                                    ['name', 'ilike', search_key],
                                    ['bed_type', 'ilike', search_key],
                                    ['rent', 'ilike', search_key],]}
                }).then(function (result){
                self.roomData = result;
                self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                    self.$('#record_list').append(`<tr class="room_item" data-index=${count}>
                            <td class="text-start" data-index=${count}>${element
                            .display_name || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.bed_type.toUpperCase() || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.rent || ''}</td></tr>`)
                    count += 1;
                })
                });
            }
            else if(roomward_btns[0].id === 'ward'){
                var search_key = $('#ward_search').val()
                var self = this;
                rpc.query({
                    model: 'hospital.ward',
                    method: 'search_read',
                    kwargs: {domain: ['|','|',
                                    ['ward_no', 'ilike', search_key],
                                    ['building_id', 'ilike', search_key],
                                    ['floor_no', 'ilike', search_key]]}
                }).then(function (result){
                self.wardData = result;
                self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="ward_item" data-index=${count}><td
                        class="text-start" data-index=${count}>${element.display_name || ''}</td>
                                                                  <td
                                                                  class="text-center" data-index=${count}>${element.building_id[1] || ''}</td>
                                                                  <td
                                                                  class="text-center" data-index=${count}>${element.floor_no || ''}</td></tr>`)
                    count += 1;
                })
                });
            }}
        },
        fetchAllocation: function(){
        //Method for fetching dictor allocation for chosen date
            var self = this;
            var selectedDate = self.$('#op_date').val();
            rpc.query({
                model: 'doctor.allocation',
                method: 'search_read',
                args: [[
                    ['slot_remaining', '>', 0],
                    ['date', '=', selectedDate],
                    ['state', '=', 'confirm']
                ]],
            }).then(function (result) {
                self.dr_lst=result
                self.$('.select_dr').html('')
                self.dr_lst.forEach(element => {
                    self.$('.select_dr').append(`
                        <option value="${element['id']}">${element.display_name}</option>
                    `)
                })
                   })
        },
        floatToTime: function(floatValue) {
        //Method to convert float value to time
            var hour = Math.floor(floatValue);
            var minute = Math.round((floatValue - hour) * 60);
            var formattedTime = hour + ":" + (minute < 10 ? "0" : "") + minute;
            return formattedTime;
        },
        patientData: [],
        //Method for fetching all patients
        fetchPatientsData: function(){
            var self = this;
            rpc.query({
                model: 'res.partner',
                method: 'fetch_patient_data',
                args: [[]]
            }).then(function (result){
                self.patientData = result;
                if (self.$('.r_active')[0]){$('.r_active')[0].classList.remove('r_active');}
                self.$('.o_patient_button')[0].classList.add('r_active');
                self.$('.r_AppntBtn').html('');
                if(self.$('#welcome')){self.$('#welcome').remove();}
                self.$('#controls').html(`<div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                                    <input class="form-control me-2" id="patient_search" style="width:275px;margin-left:145px" type="search" placeholder="Search" aria-label="Search"/>
                                    <button class="btn btn-outline-success search">Search</button>
                                    <button class="btn btn-outline-success patient_create" style="margin-right: 144px;">Create</button>
                                </div>`)
                self.$('#content').html(`<div class="row o_patientList">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Patient ID</th>
                                            <th class="text-center">Patient Name</th>
                                            <th class="text-center">Gender</th>
                                            <th class="text-center">Date of Birth</th>
                                        </tr>
                                    </thead>
                                    <tbody id="record_list"/>
                                </table>
                            </div>`);
                self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                var gender = (element.gender ? element.gender : '');
                var date_of_birth = (element.date_of_birth ? element.date_of_birth : '');
                    self.$('#record_list').append(`
                        <tr class="patient_item" data-index=${count}>
                            <td class="text-start" data-index=${count}>${element
                            .patient_seq || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.name || ''}</td>
                            <td class="text-center" data-index=${count}>${gender.toUpperCase()
                             || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${date_of_birth || ''}</td>
                        </tr>
                    `)
                    count += 1;
                })
            })
        },
        //Returns backend view of a patient
        patientBackendView: function(ev){
            var p_id = self.$(ev.target).data('patient_id')
            var self = this;
            rpc.query({
                model: 'res.partner',
                method: 'fetch_view_id',
                args: [null]
            }).then(function (result){
                    self.do_action({
                    name: _t("Create Patient"),
                    type: 'ir.actions.act_window',
                    res_model: 'res.partner',
                    res_id: p_id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[result, 'form']],
                    target: 'new',
                    })
               });
        },
        OutPatientData: [],
        //Method for fetching all outpatients
        fetchOutPatient: function(){
            var self = this;
            self.$('#view_secondary').html('');
            if (self.$('.r_active1')[0]){self.$('.r_active1')[0].classList.remove('r_active1');}
            $('.o_outpatient_button')[0].classList.add('r_active1');
            rpc.query({
                model: 'hospital.outpatient',
                method: 'search_read',
            }).then(function (result){
                self.OutPatientData = result;
                self.$('#controls').html(`
                                <div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                                    <input class="form-control me-2" id="outpatient_search" style="width:275px;margin-left:144px" type="search" placeholder="Search" aria-label="Search"/>
                                    <button class="btn btn-outline-success search">Search</button>
                                    <button class="btn btn-outline-success outpatient_create" style="margin-right: 144px;">Create</button>
                                </div>`)
                self.$('#content').html('')
                self.$('#content').html(`<div class="row o_outPatientList">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th class="text-center">OP reference</th>
                                            <th class="text-center">Slot</th>
                                            <th class="text-center">Patient ID</th>
                                            <th class="text-center">Doctor Name</th>
                                            <th class="text-center">OP Date</th>
                                            <th class="text-center">State</th>
                                        </tr>
                                    </thead>
                                    <tbody id="record_list"/>
                                </table>
                            </div>`);
                self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                var op_date = (element.op_date ? element.op_date : '');
                    self.$('#record_list').append(`
                        <tr class="outpatient_item" data-index=${count}>
                            <td class="text-center" data-index=${count}>${element
                            .display_name || ''}</td>
                            <td class="text-center" data-index=${count}>${element.slot === 0.0 ? '' : self.floatToTime(element.slot) || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.patient_id[1] || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.doctor_id[1] || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${op_date || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.state.toUpperCase() || ''}</td>
                        </tr>
                    `)
                    count += 1;
                })
            })
        },
        //Creates new outpatient
        createOutPatient : function(){
           var self = this;
            const date = new Date();
            var formattedCurrentDate = date.toISOString().split('T')[0];
            rpc.query({
                model: 'res.partner',
                method: 'fetch_patient_data',
                args: [[]]
            }).then(function (result){
            self.patient_lst=result
            self.$('.select_patient').html('')
            self.patient_lst.forEach(element => {
                self.$('.select_patient').append(`
                     <option value=""></option>
                    <option value="${element['id']}">${element.patient_seq}-${element.name}</option>
                `)
            })
           }),
           rpc.query({
               model : 'doctor.allocation',
               method :'search_read',
               args:[[['slot_remaining', '>', 0],
                                   ['date','=',formattedCurrentDate],
                                        ['state', '=', 'confirm']]],
           }).then(function (result){
            self.dr_lst=result
            self.$('.select_dr').html('')
            self.dr_lst.forEach(element => {
                self.$('.select_dr').append(`
                    <option value="${element['id']}">${element.display_name}</option>
                `)
            })
               }),
               self.$('#controls').html(``);
               self.$('#content').html(`<button id="_out_patient_history" class="btn btn-outline-primary fa fa-clock-o o_out_patient_history_button">VIEW OUTPATIENTS</button>
                <span class="text-center" ><h1 style="margin-bottom:4rem;">Create Outpatient</h1></span>
                                    <div class="row" style="margin-left:150px" id="op_table">
                                            <div class="col-m-12 col-md-6 col-lg-6">
                                                <label for="select_type"
                                                >Patient Card :</label>
                                                  <select  id="select_type" class="form-control select_type" name="group">
                                                        <option value="have_card">Have Patient Card</option>
                                                        <option value="dont_have_card">Dont have Patient Card</option>
                                                  </select>
                                                <label id="patient_label"
                                                for="sl_patient">Patient ID* :</label>
                                                <input type="text" id="sl_patient" class="form-control select_patient" autofocus="autofocus" placeholder="Select Out Patient"/>
                                                <label
                                                for="o_patient-name">Patient Name* :</label>
                                                <input type="text" id="o_patient-name" class="form-control" placeholder="Patient Name"/>
                                                <label for="o_patient-phone">Number :</label>
                                                <input type="tel" id="o_patient-phone" placeholder="Phone Number" class="form-control"/>
                                                <label for="o_patient-dob">Date of Birth :</label>
                                                <input type="date" class="form-control" id="o_patient-dob" placeholder="Date of Birth"/>
                                                <label for="o_patient_bloodgroup">Blood Group :</label>
                                                <select id="o_patient_bloodgroup" class="form-control o_bloodgroup" name="group">
                                                                            <option value="a">A</option>
                                                                            <option value="b">B</option>
                                                                            <option value="ab">AB</option>
                                                                            <option value="o">O</option>
                                                </select>
                                            </div>
                                            <div class="col-m-12 col-md-6 col-lg-6">
                                                <label for="o_patient-gender">Gender :</label>
                                                <input type="radio" class="form-check-input mr-2 o_radio_input" id="o_patient-gender" checked="true" name="gender" value="male"/>
                                                <label >Male</label>
                                                <input type="radio" class="form-check-input mr-2 o_radio_input" id="o_patient-gender" name="gender" value="female"/>
                                                <label >Female</label>
                                                <input type="radio" class="form-check-input mr-3 o_radio_input" id="o_patient-gender" name="gender" value="other"/>
                                                <label >Other</label>
                                                <label for="op_date"
                                                style="width: 100%;padding: 16px 0px;">OP Date*: </label>
                                                <input type="date"
                                                class="form-control" required
                                                id="op_date" placeholder="OP Date"/>
                                                <label for="reason">Reason :</label>
                                                <input type="text" id="reason" class="form-control reason" name="group"/>
                                                <label for="slot">Slot :</label>
                                                <input type="text" id="slot" class="form-control slot" name="group"/>
                                                <label for="sl_dr">Doctor Name*
                                                : </label>
                                                <select  id="sl_dr"
                                                class="form-control select_dr"
                                                name="group"/>
                                            </div>
                                    </div>
                                    <div class="w-100 d-flex justify-content-center align-items-center mt-4">
                                                    <button  class="btn btn-outline-success me-2 save_out_patient">Save</button>
                                                    <button  class="btn btn-outline-success saveandnew_out_patient">Save&New</button>
                                            </div>`)
                                            var currentDate = new Date();
                                            self.$('#op_date').val(currentDate.toISOString().split('T')[0])

        },
        //Method for displaying patient card
        patient_card: function() {
            if(self.$('#select_type').val() === 'dont_have_card'){
                self.$('#sl_patient').hide();
                self.$('#patient_label').hide();
            }
            else{
                self.$('#sl_patient').show();
                self.$('#patient_label').show();
            }
        },
        //Method for fetching OP details
        fetch_op_details: function () {
            var patient_id=this.$('#sl_patient').val()
            var phone=this.$('#o_patient-phone').val()
            var data={
                'patient_data':patient_id,
                'patient-phone':phone
                      }
            return data
        },
         //Method for fetching patient details
        fetch_patient_id: function () {
            var self=this
            var data=self.fetch_op_details()
            rpc.query({
                model: 'res.partner',
                method: 'reception_op_barcode',
                args:[data]
            }).then(function (result) {
                self.$('#o_patient-name').val(result.name)
                self.$('#o_patient-dob').val(result.date_of_birth)
                self.$('#o_patient-phone').val(result.phone)
                self.$('#o_patient_bloodgroup').val(result.blood_group)
                self.$('#o_patient-gender').val(result.gender)
            });
        },
         //Method for fetching patient phone number
        fetch_patient_phone:function () {
            var self = this;
            if(self.$('#select_type').val() === 'have_card')
            {
                var data=this.fetch_op_details()
                var self=this
                rpc.query({
                    model: 'res.partner',
                    method: 'reception_op_phone',
                    args:[data]
                    }).then(function (result) {
                    self.$('#sl_patient').val(result.patient_seq)
                    self.$('#o_patient-name').val(result.name)
                    self.$('#o_patient-dob').val(result.date_of_birth)
                    self.$('#o_patient_bloodgroup').val(result.blood_group)
                    self.$('#o_patient-gender').val(result.gender)
                })
            }
        },
        //Method for fetching outpatient data
       fetch_out_patient_data: function() {
            var self = this;
            var o_patient_name = self.$('#o_patient-name').val();
            var o_patient_phone = self.$('#o_patient-phone').val();
            var o_patient_dob = self.$('#o_patient-dob').val();
            var o_patient_blood_group = self.$("#o_patient_bloodgroup").val();
            var o_patient_rhtype = self.$("input[id='o_rhtype']:checked").val();
            var o_patient_gender = self.$("input[id='o_patient-gender']:checked").val();
            var patient_id = self.$('#sl_patient').val();
            var op_date = self.$('#op_date').val();
            var reason = self.$('#reason').val();
            var ticket_no = self.$('#slot').val();
            var doctor = self.$('#sl_dr').val();
            if (o_patient_name === '' || doctor === '' || op_date === '') {
                alert('Please fill out all the required fields.');
                return false; // Prevent form submission
            }
            else{
                var data = {
                    'op_name':o_patient_name,
                    'op_phone':o_patient_phone,
                    'op_blood_group':o_patient_blood_group,
                    'op_rh':o_patient_rhtype,
                    'op_gender':o_patient_gender,
                    'id' : patient_id,
                    'date' : op_date,
                    'reason' : reason,
                    'slot' : 0.00,
                    'doctor' : doctor,
                }
                if (o_patient_dob) {
                    data['op_dob'] = o_patient_dob;
                }
                return data
            }
        },
         //Method for creating outpatient
       save_out_patient_data: function(){
            var self = this;
            var data = this.fetch_out_patient_data()
            if (data != false){
                rpc.query({
                    model: 'res.partner',
                    method:'create_patient',
                    args:[data]
                }).then(function (result){
                    self.fetchOutPatient();
                });
            }
       },
        //Method for creating outpatient and clearing all fields
       o_save_and_new: function() {
        var self = this;
            var data = this.fetch_out_patient_data()
            if (data != false){
                rpc.query({
                    model: 'hospital.outpatient',
                    method: 'create_new_out_patient',
                    args: [data]
                }).then(function (){
                    self.createOutPatient();
                });
            }
       },
       InPatientData: [],
       //Method for fetching inpatient
       fetchInPatient: function(){
            var self = this;
            self.$('#view_secondary').html('');
            if (self.$('.r_active')){
                self.$('.r_active')[0].classList.remove('r_active');
            }
            self.$('.o_inpatient_button')[0].classList.add('r_active');
            rpc.query({
                model: 'hospital.inpatient',
                method: 'fetch_inpatient',
                args: [null, false]
            }).then(function (result){
                self.InPatientData = result;
                self.$('#controls').html(`<div class="row">
                    <div class="d-flex" role="search" style="max-height:40px; margin-top:10px;">
                        <input class="form-control me-2" id="inpatient_search" style="width:275px;margin-left:144px;" type="search" placeholder="Search" aria-label="Search"/>
                        <button class="btn btn-outline-success search" >Search</button>
                        <button class="btn btn-outline-success inpatient_create" style="margin-right: 144px;">Create</button>
                        </div>
                    </div>`)
                self.$('#content').html(`<div class="row o_inPatientList">
                                <table class="table table-hover">
                                    <thead><tr><th>IP reference</th>
                                            <th class="text-center">Patient ID</th>
                                            <th class="text-center">Ward</th>
                                            <th class="text-center">Bed</th>
                                            <th class="text-center">Attending Doctor</th>
                                            <th class="text-center">Hospitalized Date</th>
                                            <th class="text-center">Discharge Date</th>
                                            <th class="text-center">State</th></tr>
                                    </thead>
                                    <tbody id="record_list"/>
                                </table>
                            </div>`);
                 self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                var hosp_date = (element.hosp_date ? element.hosp_date : '');
                var discharge_date = (element.discharge_date ? element.discharge_date : '');
                self.$('#record_list').append(`
                    <tr class="inpatient_item" data-index=${count}>
                        <td class="text-start" data-index=${count}>${element.name || ''}</td>
                        <td class="text-center" data-index=${count}>${element.patient_id[1] || ''}</td>
                        <td class="text-center" data-index=${count}>${element.ward_id[1] || ''}</td>
                        <td class="text-center" data-index=${count}>${element.bed_id[1] || ''}</td>
                        <td class="text-center" data-index=${count}>${element.attending_doctor_id[1] || ''}</td>
                        <td class="text-center" data-index=${count}>${element.hosp_date || ''}</td>
                        <td class="text-center" data-index=${count}>${discharge_date || ''}</td>
                        <td class="text-center" data-index=${count}>${element.state.toUpperCase() || ''}</td>
                    </tr>
                    `);
                    count += 1;
                })
            })
        },
        //Method for creating inpatient
       createInPatient : function(){
        var self = this
           rpc.query({
           model : 'res.partner',
           method :'fetch_patient_data',
           args:[[]],
           }).then(function (result){
            self.patient_id_lst=result
            self.$('.select_patient_id').html('')
            self.patient_id_lst.forEach(element => {
                $('.select_patient_id').append(`
                    <option value="${element['id']}">${element.patient_seq}-${element.name}</option>
                `)
            })
           }),
           rpc.query({
                model : 'hr.employee',
                method :'search_read',
                args:[[['job_id.name', '=', 'Doctor']]],
           }).then(function (result){
            self.attending_dr_lst=result
            self.$('.attending_doctor_id').html('')
            self.attending_dr_lst.forEach(element => {
                self.$('.attending_doctor_id').append(`
                    <option value="${element['id']}">${element.display_name}</option>
                `)
            })
           }),
            self.$('#controls').html(``);
            self.$('#content').html(`
            <button id="_out_patient_history" class="btn btn-outline-primary fa fa-clock-o o_in_patient_history_button">VIEW INPATIENTS</button>
                                    <span class="text-center mb-3" style="margin-bottom:4rem;margin: 25px"><h1>Create Inpatient</h1></span>
                                    <table class="hsp_table" style="margin:0 auto;">
                                        <tr><td>Patient ID* : </td><td><select
                                        id="sl_patient_id" class="form-control select_patient_id" name="group"/></td></tr>
                                        <tr><td>Reason of Admission :
                                        </td><td><input type="text" class="form-control reason_of_admission" id="reason_of_admission" placeholder="Reason of Admission"/></td></tr>
                                        <tr><td>Admission Type : </td><td><select  id="admission_type" class="form-control admission_type" name="group">
                                                                            <option value="emergency">Emergency Admission</option>
                                                                            <option value="routine">Routine Admission</option>
                                        <tr><td>Attending Doctor*
                                        :</td><td><select  id="attending_doctor_id" class="form-control attending_doctor_id" name="group">
                                    </table>
                                    <center class="mt-5 pt-3">
                                    <button style="width:15%;" class="btn btn-outline-success save_in_patient">Save</button>
                                    <button style="width:15%;" class="btn btn-outline-success saveandnew_in_patient">Save&New</button>
                                    </center>

                                    </div>`)
       },
       //Method for fetching inpatient data
       fetch_in_patient_data: function(){
            var self = this;
            var patient_id = self.$('#sl_patient_id').val();
            var reason_of_admission = self.$('#reason_of_admission').val();
            var admission_type = self.$('#admission_type').val();
            var attending_doctor_id = self.$('#attending_doctor_id').val();
            if (patient_id === null || attending_doctor_id === null ||
            admission_type === null) {
                alert('Please fill out all the required fields.');
                return false; // Prevent form submission
            }
            else{
                var data = {
                    'patient_id' : patient_id,
                    'reason_of_admission' : reason_of_admission,
                    'admission_type' : admission_type,
                    'attending_doctor_id' : attending_doctor_id,
                }
                return data
            }
        },
        //Method for creating new inpatient
       save_in_patient_data: function(){
            var self = this;
            var data = this.fetch_in_patient_data()
            if (data != false || data != null || data != undefined){
                rpc.query({
                    model: 'hospital.inpatient',
                    method: 'create_new_in_patient',
                    args: [null,data]
                }).then(function (){
                   self.fetchInPatient();
            });
       }},
       //Method for creating new inpatient and clearing all fields
       i_save_and_new: function() {
        var self = this;
        var data = this.fetch_in_patient_data()
        if (data !== false){
            rpc.query({
                model: 'hospital.inpatient',
                method: 'create_new_in_patient',
                args: [null, data]
            }).then(function (){
                self.createInPatient();
            });
       }},
       //Method for fetching an inpatient
       fetch_inPatientItem : function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.InPatientData[record_id];
            this.do_action({
                    name: _t("Inpatient"),
                    type: 'ir.actions.act_window',
                    res_model: 'hospital.inpatient',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    })
        },
        //Method for fetching an outpatient
        fetch_outPatientItem : function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.OutPatientData[record_id];
            this.do_action({
                    name: _t("Outpatient"),
                    type: 'ir.actions.act_window',
                    res_model: 'hospital.outpatient',
                    res_id: record.id,
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    })
        },
        //Method for getting a patient
        fetch_patient: function(ev) {
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
            var record  = self.patientData[record_id];
            self.$('#view_secondary').html(`<div class="row r_Profile">
                                <table width="100%">
                                    <tr><td colspan="3"><h4 id="patient-name"/></td>
                                        <td rowspan="3"><img id="patient-image" width="30px"/></td>
                                    </tr><tr><td>Phone :</td>
                                        <td><p id="patient-phone" style="margin:0"/></td>
                                    </tr><tr><td>Email:</td>
                                        <td><p id="patient-email" style="margin:0"/></td>
                                    </tr><tr><td>Date of Birth :</td>
                                        <td><p id="patient-dob" style="margin:0"/></td>
                                    </tr><tr><td>Blood Group :</td>
                                        <td><p id="patient-blood" style="margin:0;text-transform: capitalize;"/></td>
                                        <td>Doctor :</td>
                                        <td><p id="patient-doctor" style="margin:0"/></td>
                                    </tr><tr><td>Gender :</td>
                                        <td><p id="patient-gender" style="margin:0"/></td>
                                    </tr><tr><td>Marital Status :</td>
                                        <td><p id="patient-status" style="margin:0"/></td>
                                    </tr>
                                </table>
                            </div><br/>
                            <button id="view_patient_profile" data-patient_id=""
                            class="btn btn-primary">View Patient</button>`)
            self.$('#patient-name').text(record.display_name || '');
            self.$('#patient-dob').text(record.date_of_birth || '');
            self.$('#patient-blood').text(`${record.blood_group} ${record.rh_type}`);
            self.$('#patient-gender').text(record.gender || '');
            self.$('#patient-status').text(record.marital_status || '');
            self.$('#patient-phone').text(record.phone || '');
            self.$('#patient-email').text(record.email || '');
            self.$('#view_patient_profile').attr('data-patient_id', record.id);
            self.$('#patient-image').attr('src', 'data:image/png;base64, '+record.image_1920);
        },
        //Method for creating new file
        fileCreate: function(ev){
            var self = this;
            const element = $(ev.target)
            var file = element[0].files[0];
            const reader = new FileReader();
            reader.onloadend = () => {
                element.attr('data-file', reader.result.split(',')[1])
            };
            reader.readAsDataURL(file);
        },
        //Method which returns the details of a patient
        fetch_patient_data: function(){
            var self = this;
            var patient_name = self.$('#patient-name').val();
            var patient_img = self.$('#patient-img').data('file');
            var patient_phone = self.$('#patient-phone').val();
            var patient_mail = self.$('#patient-mail').val();
            var patient_dob = self.$('#patient-dob').val();
            var patient_bloodgroup = self.$('#patient-bloodgroup').val();
            var patient_m_status = self.$('#patient-m-status').val() || '';
            var patient_rhtype = self.$("input[name='rhtype']:checked").val();
            var patient_gender = self.$("input[name='gender']:checked").val();
            var data = {
                'name' : patient_name,
                'blood_group' : patient_bloodgroup,
                'rh_type' : patient_rhtype,
                'gender' : patient_gender,
                'marital_status' : patient_m_status,
                'phone' : patient_phone,
                'email' : patient_mail,
                'image_1920': patient_img
            }
            if (patient_dob) {
                data['date_of_birth'] = patient_dob;
            }
            return data
        },
        //Method for creating a patient
        savePatient: function(){
            var self = this;
            var data = this.fetch_patient_data()
            rpc.query({
                model: 'res.partner',
                method: 'create',
                args: [data]
            }).then(function (){
                self.fetchPatientsData()
            })
        },
        //Method for creating a patient and clearing all fields
        save_and_new: function(){
            var self = this;
            var data = this.fetch_patient_data()
            rpc.query({
                model: 'res.partner',
                method: 'create',
                args: [data]
            }).then(function (){
                self.createPatient()
            })
        },
        //Method for creating patient
        createPatient: function(){
            self.$('#buttons').html(`<div class="col">
                                    <button id="patient_history" class="btn btn-outline-primary fa fa-clock-o o_patient_history_button">
                                        VIEW PATIENTS
                                    </button>
                                    </div>
                                </div>`);
            self.$('#controls').html('');
            self.$('#content').html(`<div class="row r_Profile">
                                    <span class="text-center mb-3 center"><h1>Create Patient</h1></span>
                                    <center class="center">
                                        <table class="hsp_table" id="patient_table">
                                            <tr class="tr_name"><td class="td_name">Name :</td><td><input type="text" id="patient-name" class="form-control" placeholder="Patient Name"/></td></tr>
                                            <tr><td>Photo :</td><td><input type="file" name="image" id="patient-img" class="form-control" accept="image/png, image/gif, image/jpeg"/></td></tr>
                                            <tr><td>Phone :</td><td><input type="tel" id="patient-phone" placeholder="Phone Number" class="form-control"/></td></tr>
                                            <tr><td>Email:</td><td><input type="email" class="form-control" id="patient-mail" placeholder="Email"/></td></tr>
                                            <tr><td>Date of Birth :</td><td><input type="date" class="form-control" id="patient-dob" placeholder="Date of Birth"/></td></tr>
                                            <tr><td>Blood Group :</td><td><select id="patient-bloodgroup" class="form-control bloodgroup" name="group">
                                                        <option value="a">A</option><option value="b">B</option><option value="ab">AB</option><option value="o">O</option></select>
                                                    <input type="radio" id="rhtype" class="form-check-input o_radio_input" checked="true" name="rhtype" value="+"/>
                                                    <label class="radio" style="font-size:15px;" for="+">+ve</label>
                                                    <input type="radio" id="rhtype" class="form-check-input o_radio_input" name="rhtype" value="-"/>
                                                    <label class="radio" style="font-size:15px;" for="-">-ve</label></td></tr>
                                            <tr><td>Gender :</td><td>
                                            <div class="d-flex align-items-center" id="p_radio">
                                                    <input type="radio" class="form-check-input mr-2 o_radio_input" checked="true" id="patient-gender" name="gender" value="male"/>
                                                    <label class="radio">Male</label>
                                                    <input type="radio" class="form-check-input mr-2 o_radio_input" id="patient-gender" name="gender" value="female"/>
                                                    <label class="radio">Female</label>
                                                    <input type="radio" class="form-check-input mr-2 o_radio_input" id="patient-gender" name="gender" value="other"/>
                                                    <label class="radio">Other</label>
                                            <div>
                                            </td></tr>
                                            <tr><td>Marital Status :</td><td><select id="patient-m-status" class="form-control marital_status" name="status">
                                                                                <option value="married">Married</option><option value="unmarried">Unmarried</option><option value="widow">Widow</option><option value="widower">Widower</option><option value="divorcee">Divorce</option>
                                                                            </select></td></tr>
                                        </table>
                                    </center>
                                    <center class="mt-3 pt-3 mb-3 save">
                                        <button class="btn btn-outline-success save_patient">Save</button>
                                        <button class="btn btn-outline-success saveandnew_patient">Save&New</button>
                                    </center>

                                    </div>`)
        },
        //Method for creating ward
        createWard: function(){
                    this.do_action({
                    name: _t("Create Ward"),
                    type: 'ir.actions.act_window',
                    res_model: 'hospital.ward',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    })
        },
        //Method for fetching appointment data
        fetchAppointmentData: function(){
            var self = this;
            self.$('#view_secondary').html('');
            if (self.$('.r_active')[0]){$('.r_active')[0].classList.remove('r_active');}
            self.$('.o_appointment_button')[0].classList.add('r_active');
            self.$('#content').html('');
            self.$('#controls').html('');
            if(self.$('#welcome')){self.$('#welcome').remove();}
            self.$('.r_AppntBtn').html(`
            <div class="row rd_buttons">
                <div class="col-lg-6 col-md-6">
                    <div id="outpatient" class="col-md-4 r_dashButton o_outpatient_button">
                        <img src="base_hospital_management/static/src/img/out_p.png" width="80px" class="out_p_image"/>
                        <p>Outpatient</p>
                    </div>
                </div>
                <div class="col-lg-6 col-md-6">
                    <div id="inpatient" class="col-md-4 r_dashButton o_inpatient_button">
                        <img src="base_hospital_management/static/src/img/in_p.png" width="80px" class="in_p_img"/>
                        <p>Inpatient</p>
                    </div>
                </div>
                </div>
                `);
                this.createOutPatient();
        },
        //Method for getting booking item
        fetch_bookingItem : function(ev){
            var self = this;
            var record_id = parseInt($(ev.target).data('index'))
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
        //Method for getting room or ward details
        fetchRoomWard: function(){
            var self = this;
            self.$('#view_secondary').html('');
            if (self.$('.r_active')[0]){$('.r_active')[0].classList.remove('r_active');}
            self.$('.o_room_ward_button')[0].classList.add('r_active');
            self.$('#content').html('');
            self.$('#controls').html('');
            if(self.$('#welcome')){$('#welcome').remove();}
            self.$('.r_AppntBtn').html(`
                                <div class="col">
                                    <div id="room" class="col-md-4 r_dashButton o_room_button">
                                        <img src="https://static.thenounproject.com/png/1183390-200.png" width="80px" class="apnmnt_img"/>
                                        <p>Rooms</p>
                                    </div>
                                </div>
                                <div class="col">
                                    <div id="ward" class="col-md-4 r_dashButton o_ward_button">
                                        <img src="https://cdn-icons-png.flaticon.com/512/1069/1069152.png" width="80px" class="apnmnt_img"/>
                                        <p>Wards</p>
                                    </div>
                                </div>`);
        },
        roomData :[],
        //Method for getting room details
        fetchRoom: function(){
            var self = this;
            if (self.$('.r_active2')[0]){$('.r_active2')[0].classList.remove('r_active2');}
            self.$('.o_room_button')[0].classList.add('r_active2');
            rpc.query({
                model: 'patient.room',
                method: 'search_read',
            }).then(function (result){
                self.roomData = result;
                self.$('#controls').html(`
                 <div class="container">
                     <div class="row">
                        <div class="d-flex search-container" role="search" style="max-height:40px; margin-top:10px;">
                            <input class="form-control me-2" id="room_search" style="width:275px;margin-left: 142px;" type="search" placeholder="Search" aria-label="Search"/>
                            <button class="btn btn-outline-success search">Search</button>
                        </div>
                     </div>
                 </div>`)
                self.$('#content').html(`<div class="row o_inPatientList">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Room No.</th>
                                            <th class="text-center">Bed Type</th>
                                            <th class="text-center">Rent</th>
                                            <th class="text-center">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody id="record_list"/>
                                </table>
                            </div>`);
                self.$('#record_list').html('');
                var count = 0;
                result.forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="room_item" data-index=${count}>
                            <td class="text-start" data-index=${count}>${element
                            .display_name || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.bed_type.toUpperCase() || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.rent || ''}</td>
                            <td class="text-center"
                            data-index=${count}>${element.state.toUpperCase() || ''}</td></tr>`)
                    count += 1;
                })
            });
        },
        wardData :[],
        //Method for getting ward details
        fetchWard: function(){
            var self = this;
            if (self.$('.r_active2')[0]){self.$('.r_active2')[0].classList.remove('r_active2');}
            self.$('.o_ward_button')[0].classList.add('r_active2');
            rpc.query({
                model: 'hospital.ward',
                method: 'search_read',
            }).then(function (result){
                self.wardData = result;
                self.$('#controls').html(`
                 <div class="container">
                            <div class="row">
                                <div class="d-flex search-container" role="search" style="max-height:40px; padding-left:0px; margin-top:10px;">
                                    <input class="form-control me-2" id="ward_search" style="width:275px;margin-left:142px;" type="search" placeholder="Search" aria-label="Search"/>
                                    <button class="btn btn-outline-success search">Search</button>
                                </div>
                            </div>
                 </div>`)
                 self.$('#content').html(`<div class="row o_inPatientList"><table
                 class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Ward Name</th>
                                                <th class="text-center">Block Name</th>
                                                <th class="text-center">Floor No.</th>
                                                <th class="text-center">No. of Beds Available</th>
                                            </tr>
                                        </thead>
                                    <tbody id="record_list"/>
                                    </table>
                                    </div>`);
                 self.$('#record_list').html('');
                 var count = 0;
                 result.forEach(element => {
                    self.$('#record_list').append(`
                        <tr class="ward_item" data-index=${count}><td
                        class="text-start" data-index=${count}>${element.display_name || ''}</td>
                          <td
                          class="text-center" data-index=${count}>${element.building_id[1] || ''}</td>
                          <td
                          class="text-center" data-index=${count}>${element.floor_no || ''}</td>
                          <td
                          class="text-center" data-index=${count}>${element.bed_count || ''}</td></tr>`)
                    count += 1;
                 })
            });
        },
    })
    core.action_registry.add('reception_dashboard_tags', ReceptionDashBoard);
    return ReceptionDashBoard;
})
