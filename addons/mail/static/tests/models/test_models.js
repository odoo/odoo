/** @odoo-module **/

import { attr, many, one, Model } from "@mail/model";

Model({
    name: "TestAddress",
    fields: {
        id: attr({
            identifying: true,
        }),
        addressInfo: attr(),
        contact: one("TestContact", {
            inverse: "address",
        }),
    },
});

Model({
    name: "TestContact",
    fields: {
        id: attr({
            identifying: true,
        }),
        address: one("TestAddress", {
            inverse: "contact",
        }),
        favorite: one("TestHobby", {
            default: { description: "football" },
        }),
        hobbies: many("TestHobby", {
            default: [{ description: "hiking" }, { description: "fishing" }],
        }),
        tasks: many("TestTask", {
            inverse: "responsible",
        }),
    },
});

Model({
    name: "TestHobby",
    fields: {
        description: attr({
            identifying: true,
        }),
    },
});

Model({
    name: "TestTask",
    fields: {
        id: attr({
            identifying: true,
        }),
        title: attr(),
        difficulty: attr({
            default: 1,
        }),
        responsible: one("TestContact", {
            inverse: "tasks",
        }),
    },
});
