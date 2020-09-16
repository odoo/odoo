odoo.define('hr/static/src/models/employee/employee.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Employee extends dependencies['mail.model'] {

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
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('user_id' in data) {
                data2.__mfield_hasCheckedUser = true;
                if (!data.user_id) {
                    data2.__mfield_user = [['unlink']];
                } else {
                    const partnerNameGet = data['user_partner_id'];
                    const partnerData = {
                        __mfield_display_name: partnerNameGet[1],
                        __mfield_id: partnerNameGet[0],
                    };
                    const userNameGet = data['user_id'];
                    const userData = {
                        __mfield_id: userNameGet[0],
                        __mfield_partner: [['insert', partnerData]],
                        __mfield_display_name: userNameGet[1],
                    };
                    data2.__mfield_user = [['insert', userData]];
                }
            }
            return data2;
        }

        /**
         * Performs the `read` RPC on the `hr.employee.public`.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        static async performRpcRead({ context, fields, ids }) {
            const employeesData = await this.env.services.rpc({
                model: 'hr.employee.public',
                method: 'read',
                args: [ids],
                kwargs: {
                    context,
                    fields,
                },
            });
            this.env.models['hr.employee'].insert(employeesData.map(employeeData =>
                this.env.models['hr.employee'].convertData(employeeData)
            ));
        }

        /**
         * Performs the `search_read` RPC on `hr.employee.public`.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {Array[]} param0.domain
         * @param {string[]} param0.fields
         */
        static async performRpcSearchRead({ context, domain, fields }) {
            const employeesData = await this.env.services.rpc({
                model: 'hr.employee.public',
                method: 'search_read',
                kwargs: {
                    context,
                    domain,
                    fields,
                },
            });
            this.env.models['hr.employee'].insert(employeesData.map(employeeData =>
                this.env.models['hr.employee'].convertData(employeeData)
            ));
        }

        /**
         * Checks whether this employee has a related user and partner and links
         * them if applicable.
         */
        async checkIsUser() {
            return this.env.models['hr.employee'].performRpcRead({
                ids: [this.__mfield_id(this)],
                fields: ['user_id', 'user_partner_id'],
                context: { active_test: false },
            });
        }

        /**
         * Gets the chat between the user of this employee and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {mail.thread|undefined}
         */
        async getChat() {
            if (!this.__mfield_user(this) && !this.__mfield_hasCheckedUser(this)) {
                await this.async(() => this.checkIsUser());
            }
            // prevent chatting with non-users
            if (!this.__mfield_user(this)) {
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with employees that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.__mfield_user(this).getChat();
        }

        /**
         * Opens a chat between the user of this employee and the current user
         * and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} [options] forwarded to @see `mail.thread:open()`
         * @returns {mail.thread|undefined}
         */
        async openChat(options) {
            const chat = await this.async(() => this.getChat());
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

        /**
         * Opens the most appropriate view that is a profile for this employee.
         */
        async openProfile() {
            return this.env.messaging.openDocument({
                id: this.__mfield_id(this),
                model: 'hr.employee.public',
            });
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

    Employee.fields = {
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this employee. This prevents doing the same RPC multiple times.
         */
        __mfield_hasCheckedUser: attr({
            default: false,
        }),
        /**
         * Unique identifier for this employee.
         */
        __mfield_id: attr(),
        /**
         * Partner related to this employee.
         */
        __mfield_partner: one2one('mail.partner', {
            inverse: '__mfield_employee',
            related: '__mfield_user.__mfield_partner',
        }),
        /**
         * User related to this employee.
         */
        __mfield_user: one2one('mail.user', {
            inverse: '__mfield_employee',
        }),
    };

    Employee.modelName = 'hr.employee';

    return Employee;
}

registerNewModel('hr.employee', factory);

});
