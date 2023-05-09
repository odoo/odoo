/** @odoo-module */
/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { SelectionPopup } from "@point_of_sale/js/Popups/SelectionPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/pos_hook";

export function useCashierSelector(
    { onCashierChanged, exclusive } = { onCashierChanged: () => {}, exclusive: false }
) {
    const popup = useService("popup");
    const { globalState } = usePos();
    useBarcodeReader(
        {
            async cashier(code) {
                const employee = globalState.employees.find(
                    (emp) => emp.barcode === Sha1.hash(code.code)
                );
                if (
                    employee &&
                    employee !== globalState.get_cashier() &&
                    (!employee.pin || (await checkPin(employee)))
                ) {
                    globalState.set_cashier(employee);
                    if (onCashierChanged) {
                        onCashierChanged();
                    }
                }
                return employee;
            },
        },
        exclusive
    );

    async function checkPin(employee) {
        const { confirmed, payload: inputPin } = await popup.add(NumberPopup, {
            isPassword: true,
            title: _t("Password?"),
        });

        if (!confirmed) {
            return false;
        }

        if (employee.pin !== Sha1.hash(inputPin)) {
            await popup.add(ErrorPopup, {
                title: _t("Incorrect Password"),
            });
            return false;
        }
        return true;
    }

    /**
     * Select a cashier, the returning value will either be an object or nothing (undefined)
     */
    return async function selectCashier() {
        if (globalState.config.module_pos_hr) {
            const employeesList = globalState.employees
                .filter((employee) => employee.id !== globalState.get_cashier().id)
                .map((employee) => {
                    return {
                        id: employee.id,
                        item: employee,
                        label: employee.name,
                        isSelected: false,
                    };
                });
            const { confirmed, payload: employee } = await popup.add(SelectionPopup, {
                title: _t("Change Cashier"),
                list: employeesList,
            });

            if (!confirmed || !employee || (employee.pin && !(await checkPin(employee)))) {
                return;
            }

            globalState.set_cashier(employee);
            if (onCashierChanged) {
                onCashierChanged();
            }
        }
    };
}
