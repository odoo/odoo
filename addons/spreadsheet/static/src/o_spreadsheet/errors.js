/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import spreadsheet from "./o_spreadsheet_extended";

const { EvaluationError, CellErrorLevel } = spreadsheet.helpers;

export class LoadingDataError extends EvaluationError {
    constructor() {
        super(_t("Loading..."), _t("Data is loading"), CellErrorLevel.silent);
    }
}
