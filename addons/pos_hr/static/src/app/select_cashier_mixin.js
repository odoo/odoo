/** @odoo-module */
/* global Sha1 */

import { _t } from "@web/core/l10n/translation";

import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

export function useCashierSelector(
    { onCashierChanged, exclusive } = { onCashierChanged: () => {}, exclusive: false }
) {
    const pos = usePos();
    const dialog = useService("dialog");
    useBarcodeReader(
        {
            async cashier(code) {
                const employee_security = pos.employee_security;
                const employee = pos.models["hr.employee"].find(
                    (emp) => employee_security[emp.id].barcode === Sha1.hash(code.code)
                );
                if (
                    employee &&
                    employee !== pos.get_cashier() &&
                    (!employee_security[employee.id].pin || (await checkPin(employee)))
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
        const employee_security = pos.employee_security;
        const inputPin = await makeAwaitable(dialog, NumberPopup, {
            formatDisplayedValue: (x) => x.replace(/./g, "•"),
            title: _t("Password?"),
        });
        if (!inputPin || employee_security[employee.id].pin !== Sha1.hash(inputPin)) {
            dialog.add(AlertDialog, {
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
        if (!pos.config.module_pos_hr) {
            return;
        }
        const employee_security = pos.employee_security;
        const employeesList = pos.models["hr.employee"]
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
        const employee = await makeAwaitable(dialog, SelectionPopup, {
            title: _t("Change Cashier"),
            list: employeesList,
        });
        if (!employee || (employee_security[employee.id].pin && !(await checkPin(employee)))) {
            return;
        }
        pos.set_cashier(employee);
        onCashierChanged?.();
    };
}
