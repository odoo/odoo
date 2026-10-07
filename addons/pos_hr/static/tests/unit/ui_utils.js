import { contains, getService } from "@web/../tests/web_test_helpers";

export async function openCashierRegister(cashierName) {
    await contains(".screen-login .btn.open-register-btn").click();
    await contains(".screen-login .select-cashier").click();
    await contains(`.modal .cashier-selection-item:contains(${cashierName})`).click();
}

export async function lockCashierRegister() {
    if (getService("ui").isSmall) {
        await contains(".pos-topheader button[aria-label='Open Menu']").click();
        await contains(".o_pos_burger_menu_buttons button:contains(Lock)").click();
    } else {
        await contains(".lock-screen").click();
    }
}
