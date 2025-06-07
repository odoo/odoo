import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    
    get showOrdersButton() {
        const cashier = this.pos.get_cashier();
        const userRole = cashier?._role;
        return userRole !== 'cashier';
    },
    
    get showCashInOutButton() {
        const cashier = this.pos.get_cashier();
        const userRole = cashier?._role;
        return userRole !== 'cashier';
    }
    
});