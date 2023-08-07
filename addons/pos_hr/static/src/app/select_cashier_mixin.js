/** @odoo-module */
/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export function useCashierSelector(
    { onCashierChanged, exclusive } = { onCashierChanged: () => {}, exclusive: false }
) {
    const popup = useService("popup");
    const pos = usePos();
    useBarcodeReader(
        {
            async cashier(code) {
                const employee = pos.employees.find((emp) => emp.barcode === Sha1.hash(code.code));
                if (
                    employee &&
                    employee !== pos.get_cashier() &&
                    (!employee.pin || (await checkPin(employee)))
                ) {
                    pos.set_cashier(employee);
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
                body: _t("Please try again."),
            });
            return false;
        }
        return true;
    }

    /**
     * Select a cashier, the returning value will either be an object or nothing (undefined)
     */
    return async function selectCashier() {
        if (pos.config.module_pos_hr) {
            const employeesList = pos.employees
                .filter((employee) => employee.id !== pos.get_cashier().id)
                .map((employee) => {
                    return {
                        id: employee.id,
                        item: employee,
                        label: employee.name,
                        isSelected: false,
                    };
                });
            if (!employeesList.length) {
                return;
            }
            const { confirmed, payload: employee } = await popup.add(SelectionPopup, {
                title: _t("Change Cashier"),
                list: employeesList,
            });

            if (!confirmed || !employee || (employee.pin && !(await checkPin(employee)))) {
                return;
            }

            pos.set_cashier(employee);
            if (onCashierChanged) {
                onCashierChanged();
            }
        }
    };
}
