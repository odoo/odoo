/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";

export function useCashierSelector({ exclusive, onScan } = { onScan: () => {}, exclusive: false }) {
    const pos = usePos();
    const dialog = useService("dialog");
    const notification = useService("notification");
    useBarcodeReader(
        {
            async cashier(code) {
                const employee = pos.models["hr.employee"].find(
                    (emp) => emp._barcode === Sha1.hash(code.code)
                );
                if (
                    employee &&
                    employee !== pos.get_cashier() &&
                    (!employee._pin || (await checkPin(employee)))
                ) {
                    onScan && onScan(employee);
                }
                return employee;
            },
        },
        exclusive
    );

    async function checkPin(employee, pin = false) {
        let inputPin = pin;
        if (!pin) {
            inputPin = await makeAwaitable(dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
            });
        } else {
            if (employee._pin !== Sha1.hash(inputPin)) {
                inputPin = await makeAwaitable(dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("Password?"),
                });
            }
        }
<<<<<<< 18.0
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
||||||| 492331d417c26dbde2eaf7426f39d7e7a87dedbf
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            dialog.add(AlertDialog, {
                title: _t("Incorrect Password"),
                body: _t("Please try again."),
=======
        if (!inputPin && typeof inputPin !== "string") {
            return false;
        }
        if (employee._pin !== Sha1.hash(inputPin)) {
            dialog.add(AlertDialog, {
                title: _t("Incorrect Password"),
                body: _t("Please try again."),
>>>>>>> b5098a171db11296ccde684021b340b8c753326c
            });
            return false;
        }
        return true;
    }

    /**
     * Select a cashier, the returning value will either be an object or nothing (undefined)
     */
    return async function selectCashier(pin = false, login = false, list = false) {
        if (!pos.config.module_pos_hr) {
            return;
        }

        const prepareList = (employees) => {
            return employees.map((employee) => {
                return {
                    id: employee.id,
                    item: employee,
                    label: employee.name,
                    isSelected: false,
                };
            });
        };

        const wrongPinNotification = () => {
            notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
        };

        let employee = false;
        const allEmployees = pos.models["hr.employee"].filter(
            (employee) => employee.id !== pos.get_cashier()?.id
        );
        const pinMatchEmployees = allEmployees.filter(
            (employee) => !pin || Sha1.hash(pin) === employee._pin
        );

        if (!pinMatchEmployees.length && !pin) {
            await ask(this.dialog, {
                title: _t("No Cashiers"),
                body: _t("There is no cashier available."),
            });
            return;
        } else if (pin && !pinMatchEmployees.length) {
            wrongPinNotification();
            return;
        }

        if (pinMatchEmployees.length > 1 || list) {
            employee = await makeAwaitable(dialog, SelectionPopup, {
                title: _t("Change Cashier"),
                list: prepareList(allEmployees),
            });

            if (!employee) {
                return;
            }

            if (pin && Sha1.hash(pin) !== employee._pin) {
                wrongPinNotification();
                return;
            }
        } else if (pinMatchEmployees.length === 1) {
            employee = pinMatchEmployees[0];
        }

        if (!pin && employee && employee._pin) {
            const result = await checkPin(employee);

            if (!result) {
                return false;
            }
        }

        if (login && employee) {
            pos.hasLoggedIn = true;
            pos.set_cashier(employee);
        }

        const currentScreen = pos.mainScreen.component.name;
        if (currentScreen === "LoginScreen" && login && employee) {
            const isRestaurant = pos.config.module_pos_restaurant;
            const selectedScreen =
                pos.previousScreen && pos.previousScreen !== "LoginScreen"
                    ? pos.previousScreen
                    : isRestaurant
                    ? "FloorScreen"
                    : "ProductScreen";

            pos.showScreen(selectedScreen);
        }

        return employee;
    };
}
