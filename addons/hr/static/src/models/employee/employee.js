/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { insert, unlink } from '@mail/model/model_field_command';

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
                data2.id = data.id;
            }
            if ('user_id' in data) {
                data2.hasCheckedUser = true;
                if (!data.user_id) {
                    data2.user = unlink();
                } else {
                    const partnerNameGet = data['user_partner_id'];
                    const partnerData = {
                        display_name: partnerNameGet[1],
                        id: partnerNameGet[0],
                    };
                    const userNameGet = data['user_id'];
                    const userData = {
                        id: userNameGet[0],
                        partner: insert(partnerData),
                        display_name: userNameGet[1],
                    };
                    data2.user = insert(userData);
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
                args: [ids, fields],
                kwargs: {
                    context,
                },
            });
            this.messaging.models['hr.employee'].insert(employeesData.map(employeeData =>
                this.messaging.models['hr.employee'].convertData(employeeData)
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
            this.messaging.models['hr.employee'].insert(employeesData.map(employeeData =>
                this.messaging.models['hr.employee'].convertData(employeeData)
            ));
        }

        /**
         * Checks whether this employee has a related user and partner and links
         * them if applicable.
         */
        async checkIsUser() {
            return this.messaging.models['hr.employee'].performRpcRead({
                ids: [this.id],
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
            if (!this.user && !this.hasCheckedUser) {
                await this.async(() => this.checkIsUser());
            }
            // prevent chatting with non-users
            if (!this.user) {
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with employees that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.user.getChat();
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
            return this.messaging.openDocument({
                id: this.id,
                model: 'hr.employee.public',
            });
        }

    }

    Employee.fields = {
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this employee. This prevents doing the same RPC multiple times.
         */
        hasCheckedUser: attr({
            default: false,
        }),
        /**
         * Unique identifier for this employee.
         */
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Partner related to this employee.
         */
        partner: one2one('mail.partner', {
            inverse: 'employee',
            related: 'user.partner',
        }),
        /**
         * User related to this employee.
         */
        user: one2one('mail.user', {
            inverse: 'employee',
        }),
    };
    Employee.identifyingFields = ['id'];
    Employee.modelName = 'hr.employee';

    return Employee;
}

registerNewModel('hr.employee', factory);
