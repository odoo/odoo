/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

registerModel({
    name: 'Employee',
    modelMethods: {
        /**
         * @param {Object} data
         * @returns {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('user_id' in data) {
                data2.hasCheckedUser = true;
                if (!data.user_id) {
                    data2.user = clear();
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
        },
        /**
         * Performs the `read` RPC on the `hr.employee.public`.
         *
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        async performRpcRead({ context, fields, ids }) {
            const employeesData = await this.messaging.rpc({
                model: 'hr.employee.public',
                method: 'read',
                args: [ids],
                kwargs: {
                    context,
                    fields,
                },
            });
            this.messaging.models['Employee'].insert(employeesData.map(employeeData =>
                this.messaging.models['Employee'].convertData(employeeData)
            ));
        },
        /**
         * Performs the `search_read` RPC on `hr.employee.public`.
         *
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {Array[]} param0.domain
         * @param {string[]} param0.fields
         */
        async performRpcSearchRead({ context, domain, fields }) {
            const employeesData = await this.messaging.rpc({
                model: 'hr.employee.public',
                method: 'search_read',
                kwargs: {
                    context,
                    domain,
                    fields,
                },
            });
            this.messaging.models['Employee'].insert(employeesData.map(employeeData =>
                this.messaging.models['Employee'].convertData(employeeData)
            ));
        },
    },
    recordMethods: {
        /**
         * Checks whether this employee has a related user and partner and links
         * them if applicable.
         */
        async checkIsUser() {
            return this.messaging.models['Employee'].performRpcRead({
                ids: [this.id],
                fields: ['user_id', 'user_partner_id'],
                context: { active_test: false },
            });
        },
        /**
         * Gets the chat between the user of this employee and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {Thread|undefined}
         */
        async getChat() {
            if (!this.user && !this.hasCheckedUser) {
                await this.checkIsUser();
            }
            if (!this.exists()) {
                return;
            }
            // prevent chatting with non-users
            if (!this.user) {
                this.messaging.notify({
                    message: this.env._t("You can only chat with employees that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.user.getChat();
        },
        /**
         * Opens a chat between the user of this employee and the current user
         * and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} [options] forwarded to @see `Thread:open()`
         * @returns {Thread|undefined}
         */
        async openChat(options) {
            const chat = await this.getChat();
            if (!this.exists()) {
                return;
            }
            if (!chat) {
                return;
            }
            await chat.open(options);
            if (!this.exists()) {
                return;
            }
            return chat;
        },
        /**
         * Opens the most appropriate view that is a profile for this employee.
         */
        async openProfile() {
            return this.messaging.openDocument({
                id: this.id,
                model: 'hr.employee.public',
            });
        },
    },
    fields: {
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
            identifying: true,
            readonly: true,
            required: true,
        }),
        /**
         * Partner related to this employee.
         */
        partner: one('Partner', {
            inverse: 'employee',
            related: 'user.partner',
        }),
        /**
         * User related to this employee.
         */
        user: one('User', {
            inverse: 'employee',
        }),
    },
});
