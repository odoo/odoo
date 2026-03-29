/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.doctorWidget = publicWidget.Widget.extend({
    selector: '#booking_form',
    events: {
        'change #booking_date': 'changeBookingDate',
        'change #doctor-department': 'updateDoctorOptions',
    },

    start() {
        return this._super(...arguments).then(() => {
            this.changeBookingDate();
        });
    },

    //  Method for check booking date
    async changeBookingDate() {
        const selectedDate =
            this.el.querySelector('#booking_date')?.value;
        const data = await rpc('/patient_booking/get_doctors', {
            selected_date: selectedDate,
            department: false,
        });
        const doctorSelect =
            this.el.querySelector('#doctor-name');
        const departmentSelect =
            this.el.querySelector('#doctor-department');
        doctorSelect.innerHTML = '';
        data.doctors.forEach((doctor) => {
            const option = document.createElement('option');
            option.value = doctor.id;
            option.textContent = doctor.name;
            doctorSelect.appendChild(option);
        });
        departmentSelect.innerHTML = '';
        departmentSelect.appendChild(document.createElement('option'));
        data.departments.forEach((dep) => {
            const option = document.createElement('option');
            option.value = dep.id;
            option.textContent = dep.name;
            departmentSelect.appendChild(option);
        });
    },

    //  Method for update doctor options
    async updateDoctorOptions() {
        const selectedDate =
            this.el.querySelector('#booking_date')?.value;
        const department =
            this.el.querySelector('#doctor-department')?.value;
        const data = await rpc('/patient_booking/get_doctors', {
            selected_date: selectedDate,
            department: department,
        });
        const doctorSelect =
            this.el.querySelector('#doctor-name');
        doctorSelect.innerHTML = '';
        data.doctors.forEach((doctor) => {
            const option = document.createElement('option');
            option.value = doctor.id;
            option.textContent = doctor.name;
            doctorSelect.appendChild(option);
        });
    },
});

export default publicWidget.registry.doctorWidget;
