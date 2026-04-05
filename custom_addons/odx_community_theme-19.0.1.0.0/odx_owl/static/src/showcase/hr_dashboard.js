/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";

class ShowcaseHrDashboard extends Component {
    static template = "odx_owl.ShowcaseHrDashboard";
    static props = {};
    setup() {
        this.state = useState({
            employee: { name: "Sarah Chen", title: "Senior Developer", department: "Engineering", photo: "" },
            leaveBalance: { annual: 18, sick: 8, personal: 3, used: 7 },
            attendance: { today: "08:32", avgWeek: "8h 15m", lateCount: 1, overtimeHours: 4.5 },
            payslips: [
                { month: "Mar 2026", gross: 8500, net: 6420, status: "paid" },
                { month: "Feb 2026", gross: 8500, net: 6380, status: "paid" },
                { month: "Jan 2026", gross: 8500, net: 6410, status: "paid" },
            ],
            holidays: [
                { date: "Apr 10", name: "Eid al-Fitr", days: 3 },
                { date: "May 1", name: "Labour Day", days: 1 },
                { date: "Jun 27", name: "Arafat Day", days: 1 },
            ],
            requests: [
                { type: "Annual Leave", from: "Apr 14", to: "Apr 18", status: "pending" },
                { type: "Sick Leave", from: "Mar 5", to: "Mar 5", status: "approved" },
            ],
        });
    }
}

// Mount on portal page
onMounted(() => {
    const el = document.getElementById("odx_showcase_hr_dashboard");
    if (el) {
        // Will be mounted by template
    }
});

export default ShowcaseHrDashboard;
