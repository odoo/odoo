/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

function factoryAddress(dependencies) {
    class Address extends dependencies['mail.model'] {
    }

    Address.fields = {
        id: attr({
            readonly: true,
            required: true,
        }),
        addressInfo: attr(),
        contact: one2one('test.contact', {
            inverse: 'address',
        }),
    };
    Address.identifyingFields = ['id'];
    Address.modelName = 'test.address';

    return Address;
}

function factoryContact(dependencies) {
    class Contact extends dependencies['mail.model'] {}

    Contact.fields = {
        id: attr({
            readonly: true,
            required: true,
        }),
        address: one2one('test.address', {
            inverse: 'contact',
        }),
        favorite: one2one('test.hobby', {
            default: insertAndReplace({ description: 'football' }),
        }),
        hobbies: one2many('test.hobby', {
            default: insertAndReplace([
                { description: 'hiking' },
                { description: 'fishing' },
            ]),
        }),
        tasks: one2many('test.task', {
            inverse: 'responsible'
        }),
    };
    Contact.identifyingFields = ['id'];
    Contact.modelName = 'test.contact';

    return Contact;
}

function factoryHobby(dependencies) {
    class Hobby extends dependencies['mail.model'] {}

    Hobby.fields = {
        description: attr({
            readonly: true,
            required: true,
        }),
    };
    Hobby.identifyingFields = ['description'];
    Hobby.modelName = 'test.hobby';

    return Hobby;
}

function factoryTask(dependencies) {
    class Task extends dependencies['mail.model'] {
    }

    Task.fields = {
        id: attr({
            readonly: true,
            required: true,
        }),
        title: attr(),
        difficulty: attr({
            default: 1,
        }),
        responsible: many2one('test.contact', {
            inverse: 'tasks'
        }),
    };
    Task.identifyingFields = ['id'];
    Task.modelName = 'test.task';

    return Task;
}

registerNewModel('test.address', factoryAddress);
registerNewModel('test.contact', factoryContact);
registerNewModel('test.hobby', factoryHobby);
registerNewModel('test.task', factoryTask);

