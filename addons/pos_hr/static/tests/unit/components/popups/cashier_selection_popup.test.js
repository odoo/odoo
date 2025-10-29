import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("displayableOptions", async () => {
    const store = await setupPosEnv();
    const employees = store.models["hr.employee"].getAll();
    const comp = await mountWithCleanup(CashierSelectionPopup, {
        props: {
            close: () => {},
            getPayload: () => {},
            employees,
        },
    });
    // Default state: visibleOptions = 5
    // shows employees up to visibleOptions (extra ones go under "more..." button)
    comp.state.visibleOptions = 1;
    const limitedEmp = comp.displayableOptions;
    expect(limitedEmp.length).toBe(1);

    //To shows all employees set visibleOptions to 0
    comp.state.visibleOptions = 0;
    const allEmp = comp.displayableOptions;
    expect(allEmp.length).toBe(2);
});
test("lock", async () => {
    const store = await setupPosEnv();
    const employees = store.models["hr.employee"].getAll();
    const comp = await mountWithCleanup(CashierSelectionPopup, {
        props: {
            close: () => {},
            getPayload: () => {},
            employees,
        },
    });
    await comp.lock();
    expect(store.router.state.current).toBe("LoginScreen");
});
test("selectEmployee", async () => {
    const store = await setupPosEnv();
    const employees = store.models["hr.employee"].getAll();
    let selectedEmployee = null;
    let closed = false;

    const comp = await mountWithCleanup(CashierSelectionPopup, {
        props: {
            employees,
            getPayload: (emp) => {
                selectedEmployee = emp;
            },
            close: () => {
                closed = true;
            },
        },
    });
    const employee = employees[0];
    comp.selectEmployee(employee);

    expect(selectedEmployee).toBe(employee);
    expect(closed).toBe(true);
});
