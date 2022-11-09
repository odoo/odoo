/** @odoo-module **/

import { attr, clear, insert, one, Model } from '@mail/model';

Model({
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
         * Opens the most appropriate view that is a profile for this employee.
         */
        async openProfile(model = 'hr.employee.public') {
            return this.messaging.openDocument({
                id: this.id,
                model: model,
            });
        },
    },
    fields: {
        /**
         * Unique identifier for this employee.
         */
        id: attr({
            identifying: true,
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
