/** @odoo-module */

const { Component } = owl;

export const EmployeeChatMixin = {
    async openChat(employeeId) {
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat({ employeeId });
    },
}
