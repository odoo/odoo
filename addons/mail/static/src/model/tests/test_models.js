/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'TestAddress',
    identifyingFields: ['id'],
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        addressInfo: attr(),
        contact: one2one('TestContact', {
            inverse: 'address',
        }),
    },
});

registerModel({
    name: 'TestContact',
    identifyingFields: ['id'],
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        address: one2one('TestAddress', {
            inverse: 'contact',
        }),
        favorite: one2one('TestHobby', {
            default: insertAndReplace({ description: 'football' }),
        }),
        hobbies: one2many('TestHobby', {
            default: insertAndReplace([
                { description: 'hiking' },
                { description: 'fishing' },
            ]),
        }),
        tasks: one2many('TestTask', {
            inverse: 'responsible'
        }),
    },
});

registerModel({
    name: 'TestHobby',
    identifyingFields: ['description'],
    fields: {
        description: attr({
            readonly: true,
            required: true,
        }),
    },
});

registerModel({
    name: 'TestTask',
    identifyingFields: ['id'],
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        title: attr(),
        difficulty: attr({
            default: 1,
        }),
        responsible: many2one('TestContact', {
            inverse: 'tasks'
        }),
    },
});
