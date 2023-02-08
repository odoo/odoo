/** @odoo-module */
import { reactive } from "@odoo/owl";
// Create global context objects
// e.g. component.env.device = new Context({ isMobile: false });
export const orderManagement = reactive({ searchString: "", selectedOrder: null });
