/** @odoo-module **/

import { attr, many, one, registerModel } from '@mail/model';

registerModel({
    name: 'TestAddress',
    fields: {
        id: attr({
            identifying: true,
        }),
        addressInfo: attr(),
        contact: one('TestContact', {
            inverse: 'address',
        }),
    },
});

registerModel({
    name: 'TestContact',
    fields: {
        id: attr({
            identifying: true,
        }),
        address: one('TestAddress', {
            inverse: 'contact',
        }),
        favorite: one('TestHobby', {
            default: { description: 'football' },
        }),
        hobbies: many('TestHobby', {
            default: [
                { description: 'hiking' },
                { description: 'fishing' },
            ],
        }),
        tasks: many('TestTask', {
            inverse: 'responsible'
        }),
    },
});

registerModel({
    name: 'TestHobby',
    fields: {
        description: attr({
            identifying: true,
        }),
    },
});

registerModel({
    name: 'TestTask',
    fields: {
        id: attr({
            identifying: true,
        }),
        title: attr(),
        difficulty: attr({
            default: 1,
        }),
        responsible: one('TestContact', {
            inverse: 'tasks'
        }),
    },
});
