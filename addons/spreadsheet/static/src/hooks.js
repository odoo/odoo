import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { stores } from "@odoo/o-spreadsheet";
import { useEffect, useExternalListener, useState } from "@odoo/owl";

import { loadBundle } from "@web/core/assets";

const { useStore, useStoreProvider, NotificationStore } = stores;
/**
 * Hook that will capture the 'Ctrl+p' press that corresponds to the user intent to print a spreadsheet.
 * It will prepare the spreadsheet for printing by:
 * - displaying it in dashboard mode.
 * - altering the spreadsheet dimensions to ensure we render the whole sheet.
 * The hook will also restore the spreadsheet dimensions to their original state after the print.
 *
 * The hook will return the print preparation function to be called manually in other contexts than pressing
 * the common keybind (through a menu for instance).
 *
 * @param {() => Model | undefined} model
 * @returns {() => Promise<void>} preparePrint
 */
export function useSpreadsheetPrint(model) {
    let frozenPrintState = undefined;
    const printState = useState({ active: false });

    useExternalListener(
        window,
        "keydown",
        async (ev) => {
            const isMeta = ev.metaKey || ev.ctrlKey;
            if (ev.key === "p" && isMeta) {
                if (!model()) {
                    return;
                }
                ev.preventDefault();
                ev.stopImmediatePropagation();
                await preparePrint();
            }
        },
        { capture: true }
    );
    useExternalListener(window, "afterprint", afterPrint);

    useEffect(
        () => {
            if (printState.active) {
                window.print();
            }
        },
        () => [printState.active]
    );

    /**
     * Returns the DOM position & dimensions such that the whole spreadsheet content is visible.
     * @returns {Rect}
     */
    function getPrintRect() {
        const sheetId = model().getters.getActiveSheetId();
        const { bottom, right } = model().getters.getSheetZone(sheetId);
        const { end: width } = model().getters.getColDimensions(sheetId, right);
        const { end: height } = model().getters.getRowDimensions(sheetId, bottom);
        return { x: 0, y: 0, width, height };
    }

    /**
     * Will alter the spreadsheet dimensions to ensure we render the whole sheet.
     * invoking this function will ultimately trigger a print of the page after a patch.
     */
    async function preparePrint() {
        if (!model()) {
            return;
        }
        await loadBundle("spreadsheet.assets_print");
        const { width, height } = model().getters.getSheetViewDimension();
        const { width: widthAndHeader, height: heightAndHeader } =
            model().getters.getSheetViewDimension();
        const viewRect = {
            x: widthAndHeader - width,
            y: heightAndHeader - height,
            width,
            height,
        };
        frozenPrintState = {
            viewRect,
            offset: model().getters.getActiveSheetScrollInfo(),
            mode: model().config.mode,
        };
        model().updateMode("dashboard");
        // reset the viewport to A1 visibility
        model().dispatch("SET_VIEWPORT_OFFSET", { offsetX: 0, offsetY: 0 });
        model().dispatch("RESIZE_SHEETVIEW", {
            ...getPrintRect(),
        });
        printState.active = true;
    }

    function afterPrint() {
        if (!model()) {
            return;
        }
        if (frozenPrintState) {
            model().dispatch("RESIZE_SHEETVIEW", frozenPrintState.viewRect);
            const { scrollX: offsetX, scrollY: offsetY } = frozenPrintState.offset;
            model().dispatch("SET_VIEWPORT_OFFSET", { offsetX, offsetY });
            model().updateMode(frozenPrintState.mode);
            frozenPrintState = undefined;
        }
        printState.active = false;
    }

    return preparePrint;
}

export function useSpreadsheetNotificationStore() {
    /**
     * Open a dialog to ask a confirmation to the user.
     *
     * @param {string} body body content to display
     * @param {Function} confirm Callback if the user press 'Confirm'
     */
    function askConfirmation(body, confirm) {
        dialog.add(ConfirmationDialog, {
            title: _t("Odoo Spreadsheet"),
            body,
            confirm,
            cancel: () => {}, // Must be defined to display the Cancel button
            confirmLabel: _t("Confirm"),
        });
    }

    /**
     * Adds a notification to display to the user
     * @param {{text: string, type: string, sticky: boolean }} notification
     */
    function notifyUser(notification) {
        notifications.add(notification.text, {
            type: notification.type,
            sticky: notification.sticky,
        });
    }

    /**
     * Open a dialog to display an error message to the user.
     *
     * @param {string} body Content to display
     * @param {function} callBack Callback function to be executed when the dialog is closed
     */
    function raiseError(body, callBack) {
        dialog.add(
            ConfirmationDialog,
            {
                title: _t("Odoo Spreadsheet"),
                body,
            },
            {
                onClose: callBack,
            }
        );
    }
    const dialog = useService("dialog");
    const notifications = useService("notification");
    useStoreProvider();
    const notificationStore = useStore(NotificationStore);
    notificationStore.updateNotificationCallbacks({
        notifyUser: notifyUser,
        raiseError: raiseError,
        askConfirmation: askConfirmation,
    });
}
