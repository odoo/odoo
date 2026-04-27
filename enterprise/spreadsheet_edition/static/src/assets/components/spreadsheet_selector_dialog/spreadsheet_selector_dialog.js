/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Notebook } from "@web/core/notebook/notebook";

import { Component, onWillStart, useState } from "@odoo/owl";
import { SpreadsheetSelectorPanel } from "./spreadsheet_selector_panel";

const LABELS = {
    PIVOT: _t("pivot"),
    LIST: _t("list"),
    LINK: _t("link"),
    GRAPH: _t("graph"),
};

/**
 * @typedef State
 * @property {Object} spreadsheets
 * @property {string} panel
 * @property {string} name
 * @property {number|null} selectedSpreadsheetId
 * @property {string} [threshold]
 * @property {Object} pagerProps
 * @property {number} pagerProps.offset
 * @property {number} pagerProps.limit
 * @property {number} pagerProps.total
 */

export class SpreadsheetSelectorDialog extends Component {
    static template = "spreadsheet_edition.SpreadsheetSelectorDialog";
    static components = { Dialog, Notebook };
    static props = {
        actionOptions: Object,
        type: String,
        threshold: { type: Number, optional: true },
        maxThreshold: { type: Number, optional: true },
        name: String,
        close: Function,
    };

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
        const orm = useService("orm");
        onWillStart(async () => {
            const spreadsheetModels = await orm.call(
                "spreadsheet.mixin",
                "get_selector_spreadsheet_models"
            );
            this.noteBookPages = spreadsheetModels.map(({ model, display_name, allow_create }) => {
                return {
                    Component: SpreadsheetSelectorPanel,
                    id: model,
                    title: display_name,
                    props: {
                        model,
                        displayBlank: allow_create,
                        onSpreadsheetSelected: this.onSpreadsheetSelected.bind(this),
                        onSpreadsheetDblClicked: this._confirm.bind(this),
                    },
                };
            });
        });
    }

    get nameLabel() {
        return _t("Name of the %s:", LABELS[this.props.type]);
    }

    get title() {
        return _t("Select a spreadsheet to insert your %s.", LABELS[this.props.type]);
    }

    /**
     * @param {number|null} id
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

        if (this.actionState.notificationMessage) {
            this.notification.add(this.actionState.notificationMessage, { type: "info" });
        }
        // the action can be preceded by a notification
        const actionOpen = action.tag === "display_notification" ? action.params.next : action;
        actionOpen.params = this._addToPreprocessingAction(actionOpen.params, threshold, name);
        this.actionService.doAction(action);
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
