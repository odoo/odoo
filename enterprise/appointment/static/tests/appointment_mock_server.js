import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("/appointment/appointment_type/create_custom", async function createCustom(request) {
    const { params } = await request.json();
    const { slots } = params;
    if (!slots.length) {
        return false;
    }
    const customAppointmentTypeID = this.env["appointment.type"].create({
        name: "Appointment with Actual User",
        staff_user_ids: [100],
        category: "custom",
        website_published: true,
    });
    const slotIDs = [];
    slots.forEach((slot) => {
        const slotID = this.env["appointment.slot"].create({
            appointment_type_id: customAppointmentTypeID,
            start_datetime: slot.start,
            end_datetime: slot.end,
            slot_type: "unique",
        });
        slotIDs.push(slotID);
    });
    return {
        appointment_type_id: customAppointmentTypeID,
        invite_url: `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${100}%5D`,
    };
});

onRpc("/appointment/appointment_type/search_create_anytime", function searchCreateAnytime() {
    let anytimeAppointmentID = this.env["appointment.type"].search([
        ["category", "=", "anytime"],
        ["staff_user_ids", "in", [100]],
    ])[0];
    if (!anytimeAppointmentID) {
        anytimeAppointmentID = this.env["appointment.type"].create({
            name: "Anytime with Actual User",
            staff_user_ids: [100],
            category: "anytime",
            website_published: true,
        });
    }
    return {
        appointment_type_id: anytimeAppointmentID,
        invite_url: `http://amazing.odoo.com/appointment/3?filter_staff_user_ids=%5B${100}%5D`,
    };
});

onRpc("/appointment/appointment_type/get_book_url", async function getBookUrl(request) {
    const { params } = await request.json();
    const { appointment_type_id } = params;
    return {
        appointment_type_id: appointment_type_id,
        invite_url: `http://amazing.odoo.com/appointment/${appointment_type_id}?filter_staff_user_ids=%5B${100}%5D`,
    };
});

onRpc(
    "/appointment/appointment_type/get_staff_user_appointment_types",
    function getStaffUserAppointmentTypes() {
        return {
            appointment_types_info: [],
        };
    }
);
