/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { create } from '@mail/model/model_field_command';

function factoryAddress(dependencies) {
    class Address extends dependencies['mail.model'] {
        static _createRecordLocalId(data) {
            if (data.id) {
                return `${this.modelName}_${data.id}`;
            } else {
                return _.uniqueId(`${this.modelName}_`);
            }
        }
    }

    Address.fields = {
        id: attr(),
        addressInfo: attr(),
        contact: one2one('test.contact', {
            inverse: 'address',
        }),
    };

    Address.modelName = 'test.address';

    return Address;
}

function factoryContact(dependencies) {
    class Contact extends dependencies['mail.model'] {}

    Contact.fields = {
        id: attr(),
        address: one2one('test.address', {
            inverse: 'contact',
        }),
        favorite: one2one('test.hobby', {
            default: create({ description: 'football' }),
        }),
        hobbies: one2many('test.hobby', {
            default: [
                create({ description: 'hiking' }),
                create({ description: 'fishing' }),
            ],
        }),
        tasks: one2many('test.task', {
            inverse: 'responsible'
        }),

    };

    Contact.modelName = 'test.contact';

    return Contact;
}

function factoryHobby(dependencies) {
    class Hobby extends dependencies['mail.model'] {}

    Hobby.fields = { description: attr() };

    Hobby.modelName = 'test.hobby';

    return Hobby;
}

function factoryTask(dependencies) {
    class Task extends dependencies['mail.model'] {
        static _createRecordLocalId(data) {
            if (data.id) {
                return `${this.modelName}_${data.id}`;
            } else {
                return _.uniqueId(`${this.modelName}_`);
            }
        }
    }

    Task.fields = {
        id: attr(),
        title: attr(),
        difficulty: attr({
            default: 1,
        }),
        responsible: many2one('test.contact', {
            inverse: 'tasks'
        }),
    };

    Task.modelName = 'test.task';

    return Task;
}

registerNewModel('test.address', factoryAddress);
registerNewModel('test.contact', factoryContact);
registerNewModel('test.hobby', factoryHobby);
registerNewModel('test.task', factoryTask);

