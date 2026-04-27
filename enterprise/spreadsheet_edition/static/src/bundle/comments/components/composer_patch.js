import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, {
    /**
     * This function overrides the original method so that when the user tries to open a the record
     * from a starred discussion linked to a spreadsheet cell thread, it can be redirected to the corresponding
     * spreadsheet record.
     * @override
     */
    get SEND_TEXT() {
        return this._isSpreadsheetCellThread() ? _t("Send") : super.SEND_TEXT;
    },

    get allowUpload() {
        return this._isSpreadsheetCellThread() ? false : super.allowUpload;
    },

    /**
     * Utility to check if the current thread is a spreadsheet cell thread.
     * @private
     */
    _isSpreadsheetCellThread() {
        const threadModel = (this.thread ?? this.message?.thread)?.model;
        return threadModel === "spreadsheet.cell.thread";
    },
});
