import { expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

export const EMPLOYEE_ROLES = ["supervised", "restrictive", "cashier", "manager"];

export const setupRolesEnv = async () => {
    const store = await setupPosEnv();
    const employees = store.models["hr.employee"].getAll();
    const env = { store };
    for (const role of EMPLOYEE_ROLES) {
        env[role] = employees.find((employee) => employee._role === role);
    }
    return env;
};

export const expectRoleAccess = (env, getter, minRole, value) => {
    const minIndex = EMPLOYEE_ROLES.indexOf(minRole);
    for (const [index, role] of EMPLOYEE_ROLES.entries()) {
        const expected = index >= minIndex ? value : !value;
        env.store.setCashier(env[role]);
        expect(env.store.accessRight[getter]).toBe(expected, {
            message: `${getter} for ${role} should be ${expected}`,
        });
    }
};
