import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

definePosModels();

test("createNewOrder", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    expect(order.employee_id.id).toBe(2);
});
test("employeeIsAdmin", async () => {
    const store = await setupPosEnv();
    const emp = store.models["hr.employee"].get(2);
    store.setCashier(emp);
    expect(store.employeeIsAdmin).toBe(true);
});
test("_getConnectedCashier", async () => {
    const store = await setupPosEnv();
    expect(store._getConnectedCashier().id).toBe(2);
});
test("shouldShowOpeningControl", async () => {
    const store = await setupPosEnv();
    const emp = store.models["hr.employee"].get(2);
    store.setCashier(emp);
    store.hasLoggedIn = true;
    expect(store.shouldShowOpeningControl()).toBe(true);
});
test("allowProductCreation", async () => {
    const store = await setupPosEnv();
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    expect(await store.allowProductCreation()).toBe(true);
    const emp = store.models["hr.employee"].get(3);
    store.setCashier(emp);
    expect(await store.allowProductCreation()).toBe(false);
});
test("addLineToCurrentOrder", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    const product_id = store.models["product.product"].get(5);
    const result = await store.addLineToCurrentOrder({
        product_id: product_id,
        product_tmpl_id: product_id.product_tmpl_id,
    });
    expect(result.order_id.employee_id.id).toBe(2);
});
test("canEditPayment", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    expect(store.canEditPayment(order)).toBe(true);
    const emp = store.models["hr.employee"].get(3);
    store.setCashier(emp);
    expect(store.canEditPayment(order)).toBe(false);
});
test("handleUrlParams prevents unauthorized access when POS is locked with pos_hr", async () => {
    const store = await setupPosEnv();
    store.config.module_pos_hr = true;
    odoo.from_backend = false;

    store.resetCashier();
    expect(store.cashier).toBe(false);
    expect(store.config.module_pos_hr).toBe(true);
    store.router.state.current = "ProductScreen";
    store.router.state.params = {};

    let navigateCalledWithLoginScreen = false;
    patchWithCleanup(store.router, {
        navigate(routeName, routeParams) {
            if (routeName === "LoginScreen") {
                navigateCalledWithLoginScreen = true;
            }
            return super.navigate(routeName, routeParams);
        },
    });

    await store.handleUrlParams();
    expect(navigateCalledWithLoginScreen).toBe(true);
});
test("keybordInputRights", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const line = await store.addLineToOrder(
        {
            product_tmpl_id: product,
            qty: 3,
            note: '[{"text":"Test 1","colorIndex":0},{"text":"Test 2","colorIndex":0}]',
        },
        order
    );
    expect(line.qty).toBe(3);
    const emp = store.models["hr.employee"].get(4);
    store.setCashier(emp);

    const orderSummary = await mountWithCleanup(OrderSummary, { props: {} });
    orderSummary.numberBuffer._handleInput("-");
    expect(line.qty).toBe(3);
});
