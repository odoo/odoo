/* global Sha1 */

import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable, ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

patch(PosAccessRightPlugin.prototype, {
    setup() {
        super.setup(...arguments);
    },
    init() {
        super.init(...arguments);
        this.pos.barcodeReader?.register(
            {
                cashier: this.barcodeCashierAction.bind(this),
            },
            // exclusive
            this.pos &&
                this.pos.router.currentScreen() === "LoginScreen" &&
                this.pos.config.module_pos_hr
        );
    },
    async barcodeCashierAction(code) {
        if (!this.pos.config.module_pos_hr) {
            return;
        }
        const employee = this.pos.models["hr.employee"].find(
            (emp) => emp._barcode === Sha1.hash(code.code)
        );
        if (
            employee &&
            employee !== this.loggedCashier &&
            (!employee._pin || (await this.checkPin(employee)))
        ) {
            this.pos.setCashier(employee);
            this.cashierLogIn();
        }
        return employee;
    },
    async checkPin(employee, pin = false) {
        let inputPin = pin;
        if (!pin) {
            inputPin = await makeAwaitable(this.pos.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
            });
        } else {
            if (employee._pin !== Sha1.hash(inputPin)) {
                inputPin = await makeAwaitable(this.pos.dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("Password?"),
                });
            }
        }
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            this.pos.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
            return false;
        }
        return true;
    },
    async selectCashier(pin = false, login = false, list = false) {
        if (!this.pos.config.module_pos_hr) {
            return;
        }

        const wrongPinNotification = () => {
            this.pos.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
        };

        let employee = false;
        const allEmployees = this.pos.models["hr.employee"].filter(
            (employee) => employee.id !== this.loggedCashier?.id
        );
        const pinMatchEmployees = allEmployees.filter(
            (employee) => !pin || Sha1.hash(pin) === employee._pin
        );

        if (!pinMatchEmployees.length && !pin) {
            await ask(this.pos.dialog, {
                title: _t("No Cashiers"),
                body: _t("There is no cashier available."),
            });
            return;
        } else if (pin && !pinMatchEmployees.length) {
            wrongPinNotification();
            return;
        }

        if (pinMatchEmployees.length > 1 || list) {
            employee = await makeAwaitable(this.pos.dialog, CashierSelectionPopup, {
                currentCashier: this.loggedCashier || undefined,
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

        const currentScreen = this.pos.router.currentScreen();
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
    },
    get loggedCashier() {
        if (this.pos.config.module_pos_hr) {
            return this.cashier;
        }
        return super.loggedCashier;
    },
    get cashierUserId() {
        if (this.pos.config.module_pos_hr) {
            return this.cashier.user_id ? this.cashier.user_id : null;
        }
        return super.cashierUserId;
    },
    hasEmployeeRole(roles = []) {
        if (!this.pos.config.module_pos_hr) {
            return true;
        }
        return roles.includes(this.cashier?._role);
    },
    get canOpenRegister() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get canCloseSession() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canPrintReport() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canSelectPrinter() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessCustomerDisplay() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canInstallApp() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get canGoToBackend() {
        return this.hasEmployeeRole(["manager"]);
    },
    get disablePartner() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canEditDetails() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get disableClickPayment() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canSplitOrder() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get disableValidateOrder() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessButton() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessProductFinancials() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableToggleFavorite() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessQuotation() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessPricelist() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessFiscalPosition() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyDiscount() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyPromoCode() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyRewards() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCashMove() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get allowProductEdition() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canSortProducts() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableLinediscount() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disablePriceButton() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCancelOrder() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canDeleteOrder() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canShowPads() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCreateBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canEditBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canDeleteBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessPaymentMethod() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canNegateQuantity() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canSnooze() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get disableToggleOrder() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canClickOrderLine() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableBackSpaceButton() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canSwitchSign() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get showEditPlanButton() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canAccessDebugMode() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessTotalDue() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canSwitchSelfAvailability() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
});
