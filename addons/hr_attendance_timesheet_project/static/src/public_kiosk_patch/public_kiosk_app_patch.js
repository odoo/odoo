/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import publicKioskModule from "@hr_attendance/public_kiosk/public_kiosk_app";
import { KioskActionChoice } from "@hr_attendance_timesheet_project/components/kiosk_action_choice/kiosk_action_choice";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

console.log("[ProjectPatch] Starting to patch kiosk app...");

// Get the class from the default export
const kioskAttendanceApp = publicKioskModule.kioskAttendanceApp;

console.log("[ProjectPatch] kioskAttendanceApp:", kioskAttendanceApp);

// Save original methods before patching
const originalOnBarcodeScanned = kioskAttendanceApp.prototype.onBarcodeScanned;
const originalOnManualSelection = kioskAttendanceApp.prototype.onManualSelection;

patch(kioskAttendanceApp.prototype, {
    /**
     * Override barcode scanning to intercept check-out action
     * Falls back to original behavior on any error
     */
    async onBarcodeScanned(barcode) {
        console.log("[ProjectPatch] onBarcodeScanned called with barcode:", barcode);

        // Check basic conditions that original method checks
        if (this.lockScanner || this.state.active_display !== 'main') {
            console.log("[ProjectPatch] Scanner locked or wrong display, skipping");
            return;
        }

        // Try our enhanced logic, fall back to original on any error
        try {
            this.lockScanner = true;
            this.ui.block();

            // First, check employee status WITHOUT toggling attendance
            console.log("[ProjectPatch] Checking employee status...");
            const checkResult = await rpc("/hr_attendance/kiosk_check_employee_status", {
                barcode: barcode,
                token: this.props.token,
            });

            console.log("[ProjectPatch] Check result:", checkResult);

            if (checkResult && checkResult.employee_id) {
                // Employee found - check if already checked in
                if (checkResult.attendance_state === 'checked_in') {
                    console.log("[ProjectPatch] Employee is checked in, showing dialog");
                    // Employee is checked in - show choice dialog
                    this.ui.unblock();
                    this.lockScanner = false;

                    await this._showActionChoiceDialog(
                        checkResult.employee_id,
                        checkResult.attendance_id,
                        checkResult.current_project_name
                    );
                    return;
                } else {
                    console.log("[ProjectPatch] Employee is checked out, calling original method");
                    // Employee is checked out - use original behavior
                    this.lockScanner = false;
                    this.ui.unblock();
                    return originalOnBarcodeScanned.call(this, barcode);
                }
            } else {
                console.log("[ProjectPatch] No employee found, calling original method");
                // No employee found - use original error handling
                this.lockScanner = false;
                this.ui.unblock();
                return originalOnBarcodeScanned.call(this, barcode);
            }
        } catch (error) {
            console.error("[ProjectPatch] Error in onBarcodeScanned, falling back to original:", error);
            // On any error, fall back to original behavior
            this.lockScanner = false;
            this.ui.unblock();
            return originalOnBarcodeScanned.call(this, barcode);
        }
    },

    /**
     * Override manual selection to intercept check-out action
     * Falls back to original behavior on any error
     */
    async onManualSelection(employeeId, enteredPin) {
        console.log("[ProjectPatch] onManualSelection called with employeeId:", employeeId);

        // Try our enhanced logic, fall back to original on any error
        try {
            // First, check employee status WITHOUT toggling attendance
            console.log("[ProjectPatch] Checking employee status...");
            const checkResult = await rpc("/hr_attendance/kiosk_check_employee_status", {
                employee_id: employeeId,
                token: this.props.token,
            });

            console.log("[ProjectPatch] Check result:", checkResult);

            if (checkResult && checkResult.employee_id) {
                // Employee found - check if already checked in
                if (checkResult.attendance_state === 'checked_in') {
                    console.log("[ProjectPatch] Employee is checked in, showing dialog");
                    // Employee is checked in - show choice dialog
                    await this._showActionChoiceDialog(
                        checkResult.employee_id,
                        checkResult.attendance_id,
                        checkResult.current_project_name
                    );
                    return;
                } else {
                    console.log("[ProjectPatch] Employee is checked out, calling original method");
                    // Employee is checked out - use original behavior
                    return originalOnManualSelection.call(this, employeeId, enteredPin);
                }
            } else {
                console.log("[ProjectPatch] No employee found, calling original method");
                // No employee found - use original behavior
                return originalOnManualSelection.call(this, employeeId, enteredPin);
            }
        } catch (error) {
            console.error("[ProjectPatch] Error in onManualSelection, falling back to original:", error);
            // On any error, fall back to original behavior
            return originalOnManualSelection.call(this, employeeId, enteredPin);
        }
    },

    /**
     * Show the action choice dialog (Check Out or Change Project)
     */
    async _showActionChoiceDialog(employeeId, attendanceId, currentProjectName) {
        console.log("[ProjectPatch] Showing action choice dialog for employee:", employeeId);
        const self = this;

        return new Promise((resolve) => {
            try {
                this.dialogService.add(
                    KioskActionChoice,
                    {
                        employeeId: employeeId,
                        attendanceId: attendanceId,
                        currentProjectName: currentProjectName,
                        onCheckOut: async () => {
                            console.log("[ProjectPatch] Check out button clicked");
                            // Perform check-out
                            try {
                                const result = await self.makeRpcWithGeolocation(
                                    '/hr_attendance/kiosk_checkout',
                                    {
                                        token: self.props.token,
                                        attendance_id: attendanceId,
                                    }
                                );

                                if (result && result.employee_name) {
                                    self.employeeData = result;
                                    self.switchDisplay("greet");
                                } else {
                                    console.error("[ProjectPatch] Check-out returned no data");
                                    self.displayNotification(_t("Check-out failed"));
                                }
                            } catch (error) {
                                console.error("[ProjectPatch] Check-out error:", error);
                                self.displayNotification(error.data?.message || _t("Check-out failed"));
                            }
                            resolve();
                        },
                        onProjectChanged: async (projectId) => {
                            console.log("[ProjectPatch] Project changed to:", projectId);
                            // Project changed successfully - show greeting
                            try {
                                const result = await rpc("/hr_attendance/kiosk_get_employee_info", {
                                    token: self.props.token,
                                    employee_id: employeeId,
                                });

                                if (result && result.employee_name) {
                                    // Modify the result to show project change message
                                    result.project_changed = true;
                                    self.employeeData = result;
                                    self.switchDisplay("greet");
                                } else {
                                    console.error("[ProjectPatch] Failed to get employee info after project change");
                                    self.displayNotification(_t("Failed to load employee info"));
                                }
                            } catch (error) {
                                console.error("[ProjectPatch] Project change error:", error);
                                self.displayNotification(error.data?.message || _t("Failed to load employee info"));
                            }
                            resolve();
                        },
                        onCancel: () => {
                            console.log("[ProjectPatch] Dialog cancelled");
                            // User cancelled - return to main screen
                            self.kioskReturn();
                            resolve();
                        },
                    },
                    {
                        onClose: () => {
                            console.log("[ProjectPatch] Dialog closed");
                            resolve();
                        }
                    }
                );
            } catch (error) {
                console.error("[ProjectPatch] Error showing dialog:", error);
                self.displayNotification(_t("An error occurred"));
                resolve();
            }
        });
    },
});

console.log("[ProjectPatch] Kiosk attendance project patch loaded successfully");
