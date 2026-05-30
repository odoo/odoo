/** @odoo-module */

import { Component, useState, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";

export class AttendanceKiosk extends Component {
    static template = "pos_kitchen_lock.AttendanceKiosk";
    static props = { onClose: Function };

    setup() {
        this.state = useState({ employees: [], loading: true, toast: null });
        onMounted(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.employees = await rpc("/pos/attendance/employees");
        } catch {
            this.state.employees = [];
        }
        this.state.loading = false;
    }

    async onEmployeeClick(emp) {
        const result = await rpc("/pos/attendance/action", { employee_id: emp.id });
        this.state.toast = result;
        await this.load();
        setTimeout(() => {
            this.state.toast = null;
        }, 2500);
    }

    get checkedInCount() {
        return this.state.employees.filter((e) => e.is_checked_in).length;
    }
}

export class AttendanceButton extends Component {
    static template = "pos_kitchen_lock.AttendanceButton";
    static components = { AttendanceKiosk };

    setup() {
        this.state = useState({ open: false });
    }
}

// Large login-screen variant — same size as Open Register
export class AttendanceLoginButton extends Component {
    static template = "pos_kitchen_lock.AttendanceLoginButton";
    static components = { AttendanceKiosk };

    setup() {
        this.state = useState({ open: false });
    }
}

// Register components so the inheriting templates can reference them
Navbar.components = { ...Navbar.components, AttendanceButton };
LoginScreen.components = { ...LoginScreen.components, AttendanceLoginButton };
