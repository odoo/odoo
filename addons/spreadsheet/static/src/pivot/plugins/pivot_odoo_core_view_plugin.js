import { OdooCoreViewPlugin } from "@spreadsheet/plugins";
import { links, isCoreCommand } from "@odoo/o-spreadsheet";
import { isDataSourceUrl, parseDataSourceUrl } from "../../data_sources/data_source_link";

const { isMarkdownLink, parseMarkdownLink } = links;

export class PivotOdooCoreViewPlugin extends OdooCoreViewPlugin {
    static getters = /** @type {const} */ (["isPivotUsedInHyperlinks"]);

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        if (isCoreCommand(cmd) || cmd.type === "UNDO" || cmd.type === "REDO") {
            this.unusedPivots = undefined;
        }
    }

    _getUnusedPivots() {
        if (this.unusedPivots) {
            return this.unusedPivots;
        }
        const unusedPivots = new Set(this.getters.getPivotIds());
        for (const sheetId of this.getters.getSheetIds()) {
            for (const cell of this.getters.getCells(sheetId)) {
                if (isMarkdownLink(cell.content)) {
                    const { url } = parseMarkdownLink(cell.content);
                    if (isDataSourceUrl(url)) {
                        const [type, id] = parseDataSourceUrl(url);
                        if (type === "pivot") {
                            unusedPivots.delete(id);
                            if (!unusedPivots.size) {
                                this.unusedPivots = [];
                                return this.unusedPivots;
                            }
                        }
                    }
                }
            }
        }
        this.unusedPivots = [...unusedPivots];
        return this.unusedPivots;
    }

    isPivotUsedInHyperlinks(pivotId) {
        return !this._getUnusedPivots().includes(pivotId);
    }
}
