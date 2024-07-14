/** @odoo-module */

export function getServerModels(year = 2022) {
    const now = luxon.DateTime.now().set({ year });
    return {
        "res.users": {
            fields: {
                id: { string: "ID", type: "integer" },
                name: { string: "Name", type: "char" },
                partner_id: { string: "Partner", type: "many2one", relation: "res.partner"},
            },
            records: [
                { id: 1, name: "User 1", partner_id: 1 },
                { id: 214, name: "User 214", partner_id: 214 },
                { id: 216, name: "User 216", partner_id: 216 },
            ],
        },
        "res.partner": {
            fields: {
                id: { string: "ID", type: "integer" },
                name: { string: "Name", type: "char" },
                email: { string: "email", type: "char" },
                phone: { string: "phone", type: "char" },
                display_name: { string: "Displayed name", type: "char" },
                user_ids: {
                    string: "Users",
                    type: "one2many",
                    relation: "res.users",
                    relation_field: "partner_id",
                },
            },
            records: [
                {
                    id: 1,
                    display_name: "Partner 1",
                    name: "Partner 1",
                    email: "partner1@test.lan",
                    phone: "0467121212",
                    user_ids: [1],
                },
                {
                    id: 214,
                    display_name: "Partner 214",
                    name: "Partner 214",
                    email: "",
                    phone: "012123123",
                    user_ids: [214],
                },
                {
                    id: 216,
                    display_name: "Partner 216",
                    name: "Partner 216",
                    email: "partner216@test.lan",
                    phone: "",
                    user_ids: [216],
                },
                {
                    id: 217,
                    display_name: "Contact Partner",
                    name: "Contact Partner",
                    email: "partner@contact.lan",
                    phone: "",
                    user_ids: [],
                },
            ],
        },
        "calendar.event": {
            fields: {
                id: { string: "ID", type: "integer" },
                user_id: { string: "User", type: "many2one", relation: "res.users" },
                partner_id: {
                    string: "Partner",
                    type: "many2one",
                    relation: "res.partner",
                    related: "user_id.partner_id",
                },
                name: { string: "Name", type: "char" },
                start_date: { string: "Start date", type: "date" },
                stop_date: { string: "Stop date", type: "date" },
                start: { string: "Start datetime", type: "datetime" },
                stop: { string: "Stop datetime", type: "datetime" },
                allday: { string: "Allday", type: "boolean" },
                partner_ids: { string: "Attendees", type: "many2many", relation: "res.partner" },
                appointment_attended: { string: "Attended", type: "boolean" },
                appointment_type_id: {
                    string: "Appointment Type",
                    type: "many2one",
                    relation: "appointment.type",
                },
            },
            records: [
                {
                    id: 1,
                    user_id: 1,
                    partner_id: 1,
                    name: "Event 1",
                    start: now.toFormat("yyyy'-01-12 10:00:00"),
                    stop: now.toFormat("yyyy'-01-12 11:00:00"),
                    allday: false,
                    appointment_attended: false,
                    partner_ids: [1, 214],
                },
                {
                    id: 2,
                    user_id: 214,
                    partner_id: 214,
                    name: "Event 2",
                    start: now.toFormat("yyyy'-01-05 10:00:00"),
                    stop: now.toFormat("yyyy'-01-05 11:00:00"),
                    allday: false,
                    appointment_attended: false,
                    partner_ids: [214, 216],
                },
                {
                    id: 3,
                    user_id: 216,
                    partner_id: 216,
                    name: "Event 3",
                    start: now.toFormat("yyyy'-01-05 10:00:00"),
                    stop: now.toFormat("yyyy'-01-05 11:00:00"),
                    allday: false,
                    appointment_attended: false,
                    partner_ids: [216, 1, 214, 217],
                },
            ],
            check_access_rights: function () {
                return Promise.resolve(true);
            },
        },
        "appointment.type": {
            fields: {
                name: { type: "char" },
                website_url: { type: "char" },
                staff_user_ids: { type: "many2many", relation: "res.users" },
                website_published: { type: "boolean" },
                slot_ids: { type: "one2many", relation: "appointment.slot" },
                schedule_based_on: {
                    type: "selection",
                    selection: [
                        ["users", "Users"],
                        ["resources", "Resources"],
                    ],
                },
                category: {
                    type: "selection",
                    selection: [
                        ["website", "Website"],
                        ["custom", "Custom"],
                    ],
                },
            },
            records: [
                {
                    id: 1,
                    name: "Very Interesting Meeting",
                    website_url: "/appointment/1",
                    website_published: true,
                    schedule_based_on: "users",
                    staff_user_ids: [214, 216],
                    category: "website",
                },
                {
                    id: 2,
                    name: "Test Appointment",
                    website_url: "/appointment/2",
                    website_published: true,
                    schedule_based_on: "users",
                    staff_user_ids: [1],
                    category: "website",
                },
            ],
        },
    };
}
