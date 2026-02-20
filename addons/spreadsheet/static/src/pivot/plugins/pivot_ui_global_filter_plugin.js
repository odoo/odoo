import { OdooUIPlugin } from "@spreadsheet/plugins";


export class PivotUIGlobalFilterPlugin extends OdooUIPlugin {

    constructor(config) {
        super(config);
        /** @type {string} */
        this.selection.observe(this, {
            handleEvent: this.handleEvent.bind(this),
        });
    }

    handleEvent(event) {
        if (!this.getters.isDashboard()) {
            return;
        }
        switch (event.type) {
            case "ZonesSelected": {
                const sheetId = this.getters.getActiveSheetId();
                const { col, row } = event.anchor.cell;
                const cell = this.getters.getCell({ sheetId, col, row });
                if (!cell?.isFormula){
                    return;
                }
                if (cell !== undefined && cell.compiledFormula.toFormulaString(this.getters).startsWith("=PIVOT.HEADER(")) {
                    const filters = this._getFiltersMatchingPivot(
                        sheetId,
                        cell.compiledFormula
                    );
                    this.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
                }
                break;
            }
        }
    }

    /**
     * Get the filter impacted by a pivot formula's argument
     * @param {CompiledFormula} compiledFormula Formula of the pivot cell
     *
     * @returns {Array<Object>}
     */
    _getFiltersMatchingPivot(sheetId, compiledFormula) {
        const functionDescription = this.getters.getFirstPivotFunction(sheetId, compiledFormula);
        if (!functionDescription) {
            return [];
        }
        const { args } = functionDescription;
        if (args.length <= 2) {
            return [];
        }
        const formulaId = args[0];
        const pivotId = this.getters.getPivotId(formulaId);
        const index = functionDescription.functionName === "PIVOT.HEADER" ? 1 : 2;
        const pivot = this.getters.getPivot(pivotId);
        const domainArgs = args.slice(index).map((value) => ({ value }));
        const domain = pivot.parseArgsToPivotDomain(domainArgs);
        return this.getters.getFiltersMatchingPivotArgs(pivotId, domain);
    }
}
