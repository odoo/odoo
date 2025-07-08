/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable, ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

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
                    employee !== pos.getCashier() &&
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
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
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

        const wrongPinNotification = () => {
            notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
        };

        let employee = false;
        const allEmployees = pos.models["hr.employee"].filter(
            (employee) => employee.id !== pos.getCashier()?.id
        );
        const pinMatchEmployees = allEmployees.filter(
            (employee) => !pin || Sha1.hash(pin) === employee._pin
        );

        if (!pinMatchEmployees.length && !pin) {
            await ask(dialog, {
                title: _t("No Cashiers"),
                body: _t("There is no cashier available."),
            });
            return;
        } else if (pin && !pinMatchEmployees.length) {
            wrongPinNotification();
            return;
        }

        if (pinMatchEmployees.length > 1 || list) {
            employee = await makeAwaitable(dialog, CashierSelectionPopup, {
                currentCashier: pos.getCashier() || undefined,
                employees: allEmployees,
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
            pos.setCashier(employee);
        }

        const currentScreen = pos.router.state.current;
        if (currentScreen === "LoginScreen" && login && employee) {
            const isRestaurant = pos.config.module_pos_restaurant;
            const selectedScreen =
                pos.previousScreen && pos.previousScreen !== "LoginScreen"
                    ? pos.previousScreen
                    : isRestaurant
                    ? "FloorScreen"
                    : "ProductScreen";
            const props = {
                orderUuid: pos.selectedOrderUuid,
            };
            if (selectedScreen === "FloorScreen") {
                delete props.orderUuid;
            }
            pos.navigate(selectedScreen, props);
        }

        return employee;
    };
}
