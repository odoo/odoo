import { Component } from "@odoo/owl";
import { DashboardBlock } from "./components/dashboard_block";

export class AddressSection extends Component {
    static template = "mysubscription.AddressSection";
    static components = { DashboardBlock };
    static props;

    onEditAddress() { alert("Edit Address"); }
    onViewInvoices() { alert("View Invoice"); }
}
