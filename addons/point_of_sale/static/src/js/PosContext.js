/** @odoo-module */
import { reactive } from "@odoo/owl";
// Create global context objects
// FIXME POSREF singletons exported by modules are not testable, this should probably be a service
export const orderManagement = reactive({ searchString: "", selectedOrder: null });
