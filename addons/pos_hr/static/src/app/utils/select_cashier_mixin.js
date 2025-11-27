/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { makeAwaitable, ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

export class CashierSelector {
    constructor() {
        this.setup(...arguments);
    }

    setup(pos, exclusive, onScan) {
        this.pos = pos;
        this.exclusive = exclusive;
        this.onScan = onScan;
        this.dialog = pos.dialog;
        this.notification = pos.notification;
    }

    // Overridden in `pos_planning` module to enrich employees with planning info (subtitles, sorting, etc.)
    getCashierSelectionList(employees) {
        return employees;
    }

    async checkPin(employee, pin = false) {
        let inputPin = pin;
        if (!pin) {
            inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
            });
        } else {
            if (employee._pin !== Sha1.hash(inputPin)) {
                inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("Password?"),
                });
            }
        }
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            this.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
            return false;
        }
        return true;
    }

    async selectCashier(pin = false, login = false, list = false) {
        if (!this.pos.config.module_pos_hr) {
            return;
        }

        const wrongPinNotification = () => {
            this.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
        };

        let employee = false;
        const allEmployees = this.pos.models["hr.employee"].filter(
            (employee) => employee.id !== this.pos.getCashier()?.id
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
            employee = await makeAwaitable(this.dialog, CashierSelectionPopup, {
                currentCashier: this.pos.getCashier() || undefined,
                employees: this.getCashierSelectionList(allEmployees),
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
            const result = await this.checkPin(employee);

            if (!result) {
                return false;
            }
        }

        if (login && employee) {
            this.pos.hasLoggedIn = true;
            this.pos.setCashier(employee);
        }

        const currentScreen = this.pos.router.state.current;
        if (currentScreen === "LoginScreen" && login && employee) {
            const selectedScreen = this.pos.defaultPage;
            const props = {
                ...selectedScreen?.params,
                orderUuid: this.pos.selectedOrderUuid,
            };
            if (selectedScreen.page === "FloorScreen") {
                delete props.orderUuid;
            }
            this.pos.navigate(selectedScreen.page, props);
        }

        return employee;
    }
}

export function useCashierSelector({ exclusive, onScan } = { onScan: () => {}, exclusive: false }) {
    const pos = usePos();
    const selector = new CashierSelector(pos, exclusive, onScan);

    useBarcodeReader(
        {
            async cashier(code) {
                const employee = pos.models["hr.employee"].find(
                    (emp) => emp._barcode === Sha1.hash(code.code)
                );
                if (
                    employee &&
                    employee !== pos.getCashier() &&
                    (!employee._pin || (await selector.checkPin(employee)))
                ) {
                    onScan && onScan(employee);
                }
                return employee;
            },
        },
        exclusive
    );

    return selector.selectCashier.bind(selector);
}
