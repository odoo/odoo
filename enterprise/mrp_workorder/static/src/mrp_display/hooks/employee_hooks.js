/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { PinPopup } from "@mrp_workorder/components/pin_popup";
import { DialogWrapper } from "@mrp_workorder/components/dialog_wrapper";
import { useState } from "@odoo/owl";

export function useConnectedEmployee(controllerType, context, actionService, dialogService ) {
    const orm = useService("orm");
    const notification = useService("notification");
    const dialog = useService("dialog");
    const imageBaseURL = `${browser.location.origin}/web/image?model=hr.employee&field=avatar_128&id=`;
    const employees = useState({
        connected: [],
        all: [],
        admin: {},
    });
    const popup = useState({
        PinPopup: {
            isShown: false,
        },
    });

    const openDialog = (id, component, props) => {
        popup[id] = {
            isShown: true,
            close: dialog.add(
                DialogWrapper,
                {
                    Component: component,
                    componentProps: props,
                },
                {
                    onClose: () => {
                        popup[id] = { isShown: false };
                    },
                }
            ),
        };
    };

    const startEmployee = async (employeeId, workorderId) => {
        await orm.call("mrp.workorder", "start_employee", [workorderId, employeeId]);
    };

    const stopEmployee = async (employeeId, workorderId) => {
        await orm.call("mrp.workorder", "stop_employee", [workorderId, [employeeId]]);
    };

    const getAllEmployees = async () => {
        const fieldsToRead = ["id", "name"];
        employees.all = await orm.searchRead("hr.employee", [], fieldsToRead);
    };

    const selectEmployee = async (employeeId, pin) => {
        const employee = employees.all.find((e) => e.id === employeeId);
        const employee_connected = employees.connected.find((e) => e.name && e.id === employee.id);
        const employee_function = employee_connected ? "logout" : "login";
        const pinValid = await orm.call("hr.employee", employee_function, [employeeId, pin]);
        if (!pinValid && popup.PinPopup.isShown) {
            return notification.add(_t("Wrong password!"), { type: "danger" });
        }
        if (!pinValid) {
            return askPin(employee);
        }

        if (employee_function === "login") {
            notification.add(_t("Logged in!"), { type: "success" });
            await getConnectedEmployees();
        } else {
            await stopAllWorkorderFromEmployee(employeeId);
            notification.add(_t("Logged out!"), { type: "success" });
        }
        dialogService.closeAll();
        await getConnectedEmployees();
    };

    const getConnectedEmployees = async (login=false) => {
        const res = await orm.call("hr.employee", "get_all_employees", [null, login]);
        if (login) {
            employees.all = res.all;
        }
        res.connected.sort(function (emp1, emp2) {
            if (emp1.workorder.length == 0) {
                return 1;
            }
            if (emp2.workorder.length == 0) {
                return -1;
            }
            return 0;
        });
        employees.connected = res.connected.map((obj) => {
            const emp = employees.all.find(e => e.id === obj.id);
            return { ...obj, name: emp.name };
        })
        const admin = employees.all.find(e => e.id === res.admin);
        if (admin) {
            employees.admin = {
                name: admin.name,
                id: admin.id,
                path: imageBaseURL + `${admin.id}`,
            }
        } else {
            employees.admin = {};
        }
    };

    const logout = async (employeeId) => {
        const success = await orm.call("hr.employee", "logout", [employeeId, false, true]);
        if (success) {
            notification.add(_t("Logged out!"), { type: "success" });
            await Promise.all([stopAllWorkorderFromEmployee(employeeId), getConnectedEmployees()]);
        } else {
            notification.add(_t("Error during log out!"), { type: "danger" });
        }
    };

    const askPin = (employee) => {
        const dialogPromise = new Promise((resolve) => {
            const onClosePopup = async(args) => {
                closePopup(args);
                resolve();
            };
            const onPinValidate = async(employeeId, pin) => {
                const res = await checkPin(employeeId, pin);
                resolve();
                return res;
            };
            openDialog("PinPopup", PinPopup, {
                popupData: { employee },
                onClosePopup,
                onPinValidate,
            });
        });
        return dialogPromise;
    };

    const toggleSessionOwner = async (employee_id, pin) => {
        if (employees.admin.id == employee_id) {
            await orm.call("hr.employee", "remove_session_owner", [employee_id]);
            await getConnectedEmployees();
        } else {
            await setSessionOwner(employee_id, pin);
        }
    };

    const setSessionOwner = async (employee_id, pin) => {
        dialogService.closeAll();
        if (employees.admin.id == employee_id && employee_id == employees.connected[0].id) {
            return;
        }
        const pinValid = await orm.call("hr.employee", "login", [employee_id, pin]);

        if (!pinValid) {
            if (pin) {
                notification.add(_t("Wrong password!"), { type: "danger" });
            }
            if (popup.PinPopup.isShown) {
                return;
            }
            await askPin({ id: employee_id });
        }
        await getConnectedEmployees();
    };

    const stopAllWorkorderFromEmployee = async (employeeId) => {
        await orm.call("hr.employee", "stop_all_workorder_from_employee", [employeeId]);
    };

    const popupAddEmployee = () => {
        actionService.doAction("mrp_workorder.action_open_employee_list", {
            props: {
                selectEmployee: (id) => selectEmployee(id),
            },
        });
    };

    const pinValidation = async (employeeId, pin) => {
        return await orm.call("hr.employee", "pin_validation", [employeeId, pin]);
    };

    const checkPin = async (employeeId, pin) => {
        if (
            employees.connected.find((e) => e.id === employeeId) &&
            employees.admin?.id != employeeId
        ) {
            setSessionOwner(employeeId, pin);
        } else {
            selectEmployee(employeeId, pin);
        }
        const pinValid = await pinValidation(employeeId, pin);
        return pinValid;
    };

    const closePopup = (popupId) => {
        const { isShown, close } = popup[popupId];
        if (isShown) {
            close();
        }
    };

    return {
        startEmployee,
        stopEmployee,
        getAllEmployees,
        getConnectedEmployees,
        logout,
        askPin,
        setSessionOwner,
        stopAllWorkorderFromEmployee,
        toggleSessionOwner,
        popupAddEmployee,
        checkPin,
        closePopup,
        pinValidation,
        selectEmployee,
        employees,
        popup,
    };
}
