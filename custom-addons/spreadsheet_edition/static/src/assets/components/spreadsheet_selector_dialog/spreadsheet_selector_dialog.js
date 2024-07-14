/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Notebook } from "@web/core/notebook/notebook";

import { Component, useState } from "@odoo/owl";

const LABELS = {
    PIVOT: _t("pivot"),
    LIST: _t("list"),
    LINK: _t("link"),
    GRAPH: _t("graph"),
};

const PAGE_LABELS = {
    SPREADSHEET: _t("Spreadsheets"),
    DASHBOARD: _t("Dashboards"),
};
/**
 * @typedef State
 * @property {Object} spreadsheets
 * @property {string} panel
 * @property {string} name
 * @property {number|false} selectedSpreadsheetId
 * @property {string} [threshold]
 * @property {Object} pagerProps
 * @property {number} pagerProps.offset
 * @property {number} pagerProps.limit
 * @property {number} pagerProps.total
 */

export class SpreadsheetSelectorDialog extends Component {
    setup() {
        /** @type {State} */
        this.state = useState({
            threshold: this.props.threshold,
            name: this.props.name,
            confirmationIsPending: false,
        });
        this.actionState = {
            getOpenSpreadsheetAction: () => {},
            notificationMessage: "",
        };
        this.notification = useService("notification");
        this.actionService = useService("action");
    }

    /**
     * @param {"SPREADSHEET" | "DASHBOARD"} title
     */
    getPageTitle(title) {
        return PAGE_LABELS[title];
    }

    get nameLabel() {
        return _t("Name of the %s:", LABELS[this.props.type]);
    }

    get title() {
        return _t("Select a spreadsheet to insert your %s.", LABELS[this.props.type]);
    }

    /**
     * @param {number|false} id
     */
    onSpreadsheetSelected({ getOpenSpreadsheetAction, notificationMessage }) {
        this.actionState = {
            getOpenSpreadsheetAction,
            notificationMessage,
        };
    }

    async _confirm() {
        if (this.state.confirmationIsPending) {
            return;
        }
        this.state.confirmationIsPending = true;
        const action = await this.actionState.getOpenSpreadsheetAction();
        const threshold = this.state.threshold ? parseInt(this.state.threshold, 10) : 0;
        const name = this.state.name.toString();

        this.notification.add(this.actionState.notificationMessage, { type: "info" });
        this.actionService.doAction({
            ...action,
            params: this._addToPreprocessingAction(action.params, threshold, name),
        });
        this.props.close();
    }

    _addToPreprocessingAction(actionParams, threshold, name) {
        return {
            ...this.props.actionOptions,
            preProcessingAsyncActionData: {
                ...this.props.actionOptions.preProcessingAsyncActionData,
                threshold,
                name,
            },
            preProcessingActionData: {
                ...this.props.actionOptions.preProcessingActionData,
                threshold,
                name,
            },
            ...actionParams,
        };
    }

    _cancel() {
        this.props.close();
    }
}

SpreadsheetSelectorDialog.template = "spreadsheet_edition.SpreadsheetSelectorDialog";
SpreadsheetSelectorDialog.components = { Dialog, Notebook };
SpreadsheetSelectorDialog.props = {
    actionOptions: Object,
    type: String,
    threshold: { type: Number, optional: true },
    maxThreshold: { type: Number, optional: true },
    name: String,
    close: Function,
};
