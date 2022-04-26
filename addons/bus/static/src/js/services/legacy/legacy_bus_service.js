/** @odoo-module **/

import { registry } from '@web/core/registry';

const { Component } = owl;

export const legacyBusService = {
    start() {
        return Component.env.services.bus_service;
    },
};

registry.category('services').add('legacy_bus_service', legacyBusService);
