odoo.define('mail/static/src/models/follower_subtype/follower_subtype.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class FollowerSubtype extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @returns {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('default' in data) {
                data2.__mfield_isDefault = data.default;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('internal' in data) {
                data2.__mfield_isInternal = data.internal;
            }
            if ('name' in data) {
                data2.__mfield_name = data.name;
            }
            if ('parent_model' in data) {
                data2.__mfield_parentModel = data.parent_model;
            }
            if ('res_model' in data) {
                data2.__mfield_resModel = data.res_model;
            }
            if ('sequence' in data) {
                data2.__mfield_sequence = data.sequence;
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

    }

    FollowerSubtype.fields = {
        __mfield_id: attr(),
        __mfield_isDefault: attr({
            default: false,
        }),
        __mfield_isInternal: attr({
            default: false,
        }),
        __mfield_name: attr(),
        // AKU FIXME: use relation instead
        __mfield_parentModel: attr(),
        // AKU FIXME: use relation instead
        __mfield_resModel: attr(),
        __mfield_sequence: attr(),
    };

    FollowerSubtype.modelName = 'mail.follower_subtype';

    return FollowerSubtype;
}

registerNewModel('mail.follower_subtype', factory);

});
