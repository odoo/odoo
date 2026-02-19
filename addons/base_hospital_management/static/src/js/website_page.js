odoo.define('base_hospital_management.website_page', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    publicWidget.registry.doctorWidget = publicWidget.Widget.extend({
    //Extends the publicWidget.Widget class to hide and show the button and calculate the distance between locations.
        selector: '#booking_form',
        events: {
            'change #booking_date': 'changeBookingDate',
            'change #doctor-department': 'updateDoctorOptions',
        },
         start: function () {
         this.changeBookingDate();
         },
        changeBookingDate: function () {
        //Update the doctor selection field
            var self = this;
            var selectedDate = this.$('#booking_date').val();
            ajax.jsonRpc('/patient_booking/get_doctors', 'call', {
                selected_date: selectedDate, department:false
            }).then(function (data) {
                self.$('#doctor-name').empty();
                // Add the fetched doctors to the dropdown
                _.each(data['doctors'], function (doctor) {
                    self.$('#doctor-name').append($('<option>', {
                        value: doctor.id,
                        text: doctor.name,
                    }));
                });
                self.$('#doctor-department').empty();
                // Add the fetched departments to the dropdown
                self.$('#doctor-department').append($('<option>'));
                _.each(data['departments'], function (dep) {
                    self.$('#doctor-department').append($('<option>', {
                        value: dep.id,
                        text: dep.name,
                    }));
                });
            });
        },
        updateDoctorOptions: function () {
        //Update the doctor selection field
            var self = this;
            var selectedDate = this.$('#booking_date').val();
            var department = this.$('#doctor-department').val();
            ajax.jsonRpc('/patient_booking/get_doctors', 'call', {
                selected_date: selectedDate, department:department
            }).then(function (data) {
                self.$('#doctor-name').empty();
                // Add the fetched doctors to the dropdown
                 _.each(data['doctors'], function (doctor) {
                    self.$('#doctor-name').append($('<option>', {
                        value: doctor.id,
                        text: doctor.name,
                    }));
                });
            });
        },
    });
    return publicWidget.registry.doctorWidget;
});
