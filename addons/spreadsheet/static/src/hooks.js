import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { stores } from "@odoo/o-spreadsheet";

const { useStore, useStoreProvider, NotificationStore } = stores;

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
