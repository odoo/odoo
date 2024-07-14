/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { DEFAULT_LINES_NUMBER } from "@spreadsheet/helpers/constants";
import { InputDialog } from "@spreadsheet_edition/bundle/actions/input_dialog/input_dialog";

import { Spreadsheet, Model } from "@odoo/o-spreadsheet";

import { useSubEnv, Component } from "@odoo/owl";

/**
 * @typedef {Object} User
 * @property {string} User.name
 * @property {string} User.id
 */

/**
 * Component wrapping the <Spreadsheet> component from o-spreadsheet
 * to add user interactions extensions from odoo such as notifications,
 * error dialogs, etc.
 */
export class SpreadsheetComponent extends Component {
    get model() {
        return this.props.model;
    }
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notifications = useService("notification");
        this.dialog = useService("dialog");

        useSubEnv({
            getLinesNumber: this._getLinesNumber.bind(this),
            notifyUser: this.notifyUser.bind(this),
            raiseError: this.raiseError.bind(this),
            askConfirmation: this.askConfirmation.bind(this),
        });
    }

    /**
     * Open a dialog to ask a confirmation to the user.
     *
     * @param {string} body body content to display
     * @param {Function} confirm Callback if the user press 'Confirm'
     */
    askConfirmation(body, confirm) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Odoo Spreadsheet"),
            body,
            confirm,
            cancel: () => {}, // Must be defined to display the Cancel button
            confirmLabel: _t("Confirm"),
        });
    }

    _getLinesNumber(callback) {
        this.dialog.add(InputDialog, {
            body: _t("Select the number of records to insert"),
            confirm: callback,
            title: _t("Re-insert list"),
            inputValue: DEFAULT_LINES_NUMBER,
            inputType: "number",
        });
    }

    /**
     * Adds a notification to display to the user
     * @param {{text: string, type: string, sticky: boolean }} notification
     */
    notifyUser(notification) {
        this.notifications.add(notification.text, {
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
    raiseError(body, callBack) {
        this.dialog.add(
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
}

SpreadsheetComponent.template = "spreadsheet_edition.SpreadsheetComponent";
SpreadsheetComponent.components = { Spreadsheet };
Spreadsheet._t = _t;
SpreadsheetComponent.props = {
    model: Model,
};
