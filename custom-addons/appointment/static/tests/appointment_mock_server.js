/** @odoo-module **/

import { registry } from "@web/core/registry";

const mockRegistry = registry.category("mock_server");

mockRegistry.add("/appointment/appointment_type/create_custom", function (route, args) {
    const slots = args.slots;
    if (slots.length === 0) {
        return false;
    }
    const customAppointmentTypeID = this.mockCreate('appointment.type', {
        name: "Appointment with Actual User",
        staff_user_ids: [1],
        category: 'custom',
        website_published: true,
    });
    let slotIDs = [];
    slots.forEach(slot => {
        const slotID = this.mockCreate('appointment.slot', {
            appointment_type_id: customAppointmentTypeID,
            start_datetime: slot.start,
            end_datetime: slot.end,
            slot_type: 'unique',
        });
        slotIDs.push(slotID);
    });
    return {
        appointment_type_id: customAppointmentTypeID,
        invite_url: `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${1}%5D`,
    };
});

mockRegistry.add("/appointment/appointment_type/search_create_anytime", function (route, args) {
    let anytimeAppointmentID = this.mockSearch(
        'appointment.type',
        [[['category', '=', 'anytime'], ['staff_user_ids', 'in', [1]]]],
        {},
    )[0];
    if (!anytimeAppointmentID) {
        anytimeAppointmentID = this.mockCreate('appointment.type', {
            name: "Anytime with Actual User",
            staff_user_ids: [1],
            category: 'anytime',
            website_published: true,
        });
    }
    return {
        appointment_type_id: anytimeAppointmentID,
        invite_url: `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${1}%5D`,
    };
});

mockRegistry.add("/appointment/appointment_type/get_book_url", function (route, args) {
    const appointment_type_id = args.appointment_type_id;
    return {
        appointment_type_id: appointment_type_id,
        invite_url: `http://amazing.odoo.com/appointment/${appointment_type_id}?filter_staff_user_ids=%5B${1}%5D`,
    }
});

mockRegistry.add("/appointment/appointment_type/get_staff_user_appointment_types", function (route, args) {
    return {appointment_types_info: []};
});
