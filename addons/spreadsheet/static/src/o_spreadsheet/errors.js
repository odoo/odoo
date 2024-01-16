/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registries, EvaluationError } from "@odoo/o-spreadsheet";

const LOADING_ERROR = _t("Loading...");

registries.errorTypes.add(LOADING_ERROR);

/**
 * @param {{ value: unknown }} valueOrError
 * @returns {boolean}
 */
export function isLoadingError(valueOrError) {
    return valueOrError.value === LOADING_ERROR;
}

export class LoadingDataError extends EvaluationError {
    constructor() {
        super("", LOADING_ERROR);
    }
}
