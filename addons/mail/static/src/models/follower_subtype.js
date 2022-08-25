/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'FollowerSubtype',
    modelMethods: {
        /**
         * @param {Object} data
         * @returns {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('default' in data) {
                data2.isDefault = data.default;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('internal' in data) {
                data2.isInternal = data.internal;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            if ('parent_model' in data) {
                data2.parentModel = data.parent_model;
            }
            if ('res_model' in data) {
                data2.resModel = data.res_model;
            }
            if ('sequence' in data) {
                data2.sequence = data.sequence;
            }
            return data2;
        },
    },
    fields: {
        followerSubtypeViews: many('FollowerSubtypeView', {
            inverse: 'subtype',
            isCausal: true,
        }),
        id: attr({
            identifying: true,
        }),
        isDefault: attr({
            default: false,
        }),
        isInternal: attr({
            default: false,
        }),
        name: attr(),
        // AKU FIXME: use relation instead
        parentModel: attr(),
        // AKU FIXME: use relation instead
        resModel: attr(),
        sequence: attr({
            default: 1,
        }),
    },
});
