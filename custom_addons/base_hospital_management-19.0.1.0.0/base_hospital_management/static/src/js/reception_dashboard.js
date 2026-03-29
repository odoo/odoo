/** @odoo-module */
import { registry} from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class ReceptionDashBoard extends Component{
    setup() {
        this.patient_creation = useRef('patient_creation');
        this.inpatient = useRef('inpatient');
        this.out_patient = useRef('out-patient');
        this.rd_buttons = useRef('rd_buttons');
        this.room_ward = useRef('room_ward');
        this.ward = useRef('ward');
        this.room = useRef('room');
        this.action = useService('action');
        this.orm = useService("orm");
        this.state = useState({
            patient_lst : [],
            dr_lst: [],
            patient_id_lst: [],
            attending_dr_lst: [],
            ward_data : [],
            room_data : [],
            });
        onMounted(async () => {
                await this.createPatient();
        });
    }

    //  Method for creating patient
    createPatient(){
        document.querySelectorAll('.r_active').forEach(el => {
            el.classList.remove('r_active');
        });
        document.querySelector('.o_patient_button').classList.add('r_active');
        this.room_ward.el.classList.add("d-none")
        this.patient_creation.el.classList.remove("d-none");
        this.out_patient.el.classList.add("d-none");
        this.inpatient.el.classList.add("d-none");
        this.rd_buttons.el.classList.add("d-none");
        this.ward.el.classList.add("d-none");
        this.room.el.classList.add("d-none");
    }

    //  Method for save patient
    async savePatient (){
        var data = await this.fetch_patient_data()
        if( data['name']=="" || data['phone']==""){
            alert("Please fill the name and phone")
            return;
        }
        await this.orm.call('res.partner','create',[[data]]).then(function (){
           alert("the patient record has been created")
           window.location.reload()
        })
    }

    //  Method which returns the details of a patient given in the form
    fetch_patient_data (){
        var patient_name = document.querySelector('#patient-name').value;
        var patient_img = document.querySelector('#patient-img').dataset.file;
        var patient_phone = document.querySelector('#patient-phone').value;
        var patient_mail = document.querySelector('#patient-mail').value;
        var patient_dob = document.querySelector('#patient-dob').value;
        var patient_bloodgroup = document.querySelector('#patient-bloodgroup').value;
        var patient_m_status = document.querySelector('#patient-m-status').value || '';
        var patient_rhtype = document.querySelector("input[name='rhtype']:checked")?.value;
        var patient_gender = document.querySelector("input[name='gender']:checked")?.value;
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
    }

    //  Method on clicking  appointment button
    fetchAppointmentData (){
        document.querySelectorAll('.r_active').forEach(el => {
            el.classList.remove('r_active');
        });
        document.querySelector('.o_appointment_button').classList.add('r_active');
        this.room_ward.el.classList.add("d-none")
        this.patient_creation.el.classList.add("d-none");
        this.out_patient.el.classList.remove("d-none");
        this.inpatient.el.classList.add("d-none");
        this.rd_buttons.el.classList.remove("d-none");
        this.ward.el.classList.add("d-none");
        this.room.el.classList.add("d-none");
        this.createOutPatient();
    }

    //  Creates new outpatient
    async createOutPatient (){
        var self = this;
        const date = new Date();
        var formattedCurrentDate = date.toISOString().split('T')[0];
        const result = await this.orm.call('res.partner','fetch_patient_data',[],)
        this.state.patient_lst = result
        self.patient_lst=result
        const doctorResult = await this.orm.call('doctor.allocation','search_read',[])
        this.state.dr_lst = doctorResult;
        document.querySelector('#controls').innerHTML = ``;
        var currentDate = new Date();
        document.querySelector('#op_date').value = currentDate.toISOString().split('T')[0];
    }

    //  Method for creating inpatient
    async createInPatient (){
        var self = this
        this.room_ward.el.classList.add("d-none")
        this.patient_creation.el.classList.add("d-none");
        this.out_patient.el.classList.add("d-none");
        this.inpatient.el.classList.remove("d-none");
        this.ward.el.classList.add("d-none");
        this.room.el.classList.add("d-none");
        var domain = [['job_id.name', '=', 'Doctor']];
        const patientResult = await this.orm.call('res.partner','fetch_patient_data',[])
        self.patient_id_lst = patientResult
        this.state.patient_id_lst = patientResult;
        const attendingResult = await this.orm.call('hr.employee','fetch_doctors_for_reception',[domain])
        this.state.attending_dr_lst = attendingResult;
    }

    //  Method for saving outpatient
    async save_out_patient_data() {
        var self = this;
        var data = await self.fetch_out_patient_data();
        if (data !== false) {
            var result = await this.orm.call('res.partner', 'create_patient', [data]);
            alert('The outpatient is created');
            document.querySelector('#o_patient-name').value = '';
            document.querySelector('#sl_patient').value = '';
            document.querySelector('#o_patient-phone').value = '';
            document.querySelector('#o_patient-dob').value = '';
        }
    }

    //  Method for displaying patient card
    patient_card () {
        const selectType = document.querySelector('#select_type').value;
        const patientSelect = document.querySelector('#sl_patient');
        const patientLabel = document.querySelector('#patient_label');
        if(selectType === 'dont_have_card'){
            patientSelect.style.display = 'none';
            patientLabel.style.display = 'none';
        }
        else{
            patientSelect.style.display = 'block';
            patientLabel.style.display = 'block';
        }
    }

    //  Method for fetching OP details
    async fetch_op_details () {
        var patient_id = document.querySelector('#sl_patient').value;
        var phone = document.querySelector('#o_patient-phone').value;
        var data = {
            'patient_data': patient_id,
            'patient-phone': phone
        }
        return data
    }

    //  Method for fetching patient details
    async fetch_patient_id () {
        var data = await this.fetch_op_details()
        await this.orm.call('res.partner', 'reception_op_barcode',[data]
        ).then(function (result) {
            document.querySelector('#o_patient-name').value = result.name;
            document.querySelector('#o_patient-dob').value = result.date_of_birth;
            document.querySelector('#o_patient_bloodgroup').value = result.blood_group;
            document.querySelector('#o_patient-gender').value = result.gender;
            if (result.phone){
                document.querySelector('#o_patient-phone').value = result.phone;
            }
        });
    }

    //  Method for fetching outpatient data
    async fetch_out_patient_data () {
        var o_patient_name = document.querySelector('#o_patient-name').value;
        var o_patient_phone = document.querySelector('#o_patient-phone').value;
        var o_patient_dob = document.querySelector('#o_patient-dob').value;
        var o_patient_blood_group = document.querySelector("#o_patient_bloodgroup").value;
        var o_patient_rhtype = document.querySelector("input[id='o_rhtype']:checked")?.value;
        var o_patient_gender = document.querySelector("input[id='o_patient-gender']:checked")?.value;
        var patient_id = document.querySelector('#sl_patient').value;
        var op_date = document.querySelector('#op_date').value;
        var reason = document.querySelector('#reason').value;
        var ticket_no = document.querySelector('#slot').value;
        var doctor = document.querySelector('#sl_dr').value;
        if (o_patient_name === '' || doctor === '' || op_date === '') {
            alert('Please fill out all the required fields.');
            return false;
        }
        else{
            var data = {
                'op_name': o_patient_name,
                'op_phone': o_patient_phone,
                'op_blood_group': o_patient_blood_group,
                'op_rh': o_patient_rhtype,
                'op_gender': o_patient_gender,
                'patient_id' : patient_id,
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
    }

    //  Method for fetching inpatient data
    async fetch_in_patient_data (){
        var patient_id = document.querySelector('#sl_patient_id').value;
        var reason_of_admission = document.querySelector('#reason_of_admission').value;
        var admission_type = document.querySelector('#admission_type').value;
        var attending_doctor_id = document.querySelector('#attending_doctor_id').value;
        if (patient_id === null || attending_doctor_id === null || admission_type === null) {
            alert('Please fill out all the required fields.');
            return false;
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
    }

    //  Method for creating new inpatient
    async save_in_patient_data (){
        var data = await this.fetch_in_patient_data()
        if (data != false || data != null || data != undefined){
            this.orm.call('hospital.inpatient','create_new_in_patient',[null,data]
            ).then(function (){
                alert('Inpatient is created');
                document.querySelector('#sl_patient_id').value = '';
                document.querySelector('#reason_of_admission').value = '';
                document.querySelector('#admission_type').value = '';
                document.querySelector('#attending_doctor_id').value = '';
        });
        }
    }

    //  Method for getting room or ward details
    fetchRoomWard (){
        const viewSecondary = document.querySelector('#view_secondary');
        if (viewSecondary) {
            viewSecondary.innerHTML = '';
        }
        this.room_ward.el.classList.remove("d-none")
        this.patient_creation.el.classList.add("d-none");
        this.out_patient.el.classList.add("d-none");
        this.inpatient.el.classList.add("d-none");
        this.rd_buttons.el.classList.add("d-none");
         document.querySelectorAll('.r_active').forEach(el => {
            el.classList.remove('r_active');
        });
        document.querySelector('.o_room_ward_button').classList.add('r_active');
    }

    //  Method for getting ward details
    async fetchWard (){
        this.ward.el.classList.remove("d-none");
        this.room.el.classList.add("d-none");
        document.querySelectorAll('.r_active2').forEach(el => {
            el.classList.remove('r_active2');
        });
        document.querySelector('.o_ward_button').classList.add('r_active2');
        var result = await this.orm.call('hospital.ward','fetch_ward_details',)
        this.state.ward_data = result
    }

    //  Method for getting room details
    async fetchRoom (){
        this.room.el.classList.remove("d-none");
        this.ward.el.classList.add("d-none");
         document.querySelectorAll('.r_active2').forEach(el => {
            el.classList.remove('r_active2');
        });
        document.querySelector('.o_room_button').classList.add('r_active2');
        var result= await this.orm.call('patient.room','fetch_rooms_details',)
        this.state.room_data = result
    }
}
ReceptionDashBoard.template = "ReceptionDashboard"
registry.category('actions').add('reception_dashboard_tags', ReceptionDashBoard);
