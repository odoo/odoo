import * as spreadsheet from "@odoo/o-spreadsheet";

const { isEvaluationError, isMatrix, deepEquals } = spreadsheet.helpers;
const { NotAvailableError } = spreadsheet;

export class ListPresentationLayer {
    constructor(getters, listId, definition, dataSource) {
        this.getters = getters;
        this.id = listId;
        this.definition = definition;
        this.dataSource = dataSource;
        this.computeCache = {};
    }

    getListHeaderValue(path) {
        const columnDef = this.definition.columns.find((col) => col.name === path);
        return columnDef?.string || this.dataSource.getListHeaderValue(path);
    }

    getListValuesAndFormats(rowCount) {
        if (rowCount === undefined) {
            throw new Error("The number of rows to fetch must be specified");
        }
        const columns = this.definition.columns.filter((col) => !col.hidden);

        if (columns.length === 0) {
            return { value: this.getters.getListDisplayName(this.id) };
        }

        const computedColumns = columns.filter((col) => !!col.computedBy);

        const computedSymbols = new Set(
            computedColumns.flatMap((col) => {
                const formula = this.getters.getListCompiledMeasureFormula(this.id, col.name);
                return formula.tokens
                    .filter((token) => token.type === "SYMBOL")
                    .map((t) => t.value);
            })
        );

        const columnToFetch = [];
        for (const col of this.definition.columns) {
            if ((!col.hidden || computedSymbols.has(col.string)) && !col.computedBy) {
                columnToFetch.push(col);
            }
        }

        if (columnToFetch.length) {
            columnToFetch.forEach((col) => this.dataSource.addFieldPathToFetch(col.name));
            // triggers the fetch of the list values up to `rowCount` to fill the datasource cache (if not already done)
            this.dataSource.getListCellValue(rowCount, columnToFetch[0]?.name);
        }

        const numberRecordsToLoad = Math.min(this.dataSource.data.length, rowCount);
        const valuesAndFormats = [];
        for (const column of columns) {
            if (column.hidden) {
                continue;
            }
            const currentColumn = [];
            currentColumn.push({ value: this.getListHeaderValue(column.name) });
            for (let position = 0; position < numberRecordsToLoad; position++) {
                const cellValueAndFormat = this.getListCellValueAndFormat(column, position);
                currentColumn.push(cellValueAndFormat);
            }
            valuesAndFormats.push(currentColumn);
        }
        return valuesAndFormats;
    }

    getListCellValueAndFormat(column, position) {
        if (column && column.computedBy) {
            return this.computeCellValue(column, position);
        }
        return this._getListCellValueAndFormat(position, column.name);
    }

    _getListCellValueAndFormat(position, path) {
        // shortcut to pre-fill the fetch list (spares a round of server call)
        this.dataSource.addFieldPathToFetch(path);
        const value = this.dataSource.getListCellValue(position, path);
        if (typeof value === "object" && isEvaluationError(value.value)) {
            return value;
        }
        const field = this.dataSource.getFieldFromFieldPath(path);
        const format = this._getListFormat(position, path, field);
        return { value, format };
    }

    computeCellValue(column, position) {
        const cacheKey = `${column.name}_${position}`;
        if (this.computeCache[cacheKey]) {
            return this.computeCache[cacheKey];
        }
        const formula = this.getters.getListCompiledMeasureFormula(this.id, column.name);
        const getSymbolValue = (symbol) => {
            const symbolColumn = this.definition.columns.find((col) => col.string === symbol);
            if (!symbolColumn) {
                return new NotAvailableError();
            } else if (symbolColumn.string === column.string) {
                return new NotAvailableError(); // TODO switch to Cycle error
            }
            return this.getListCellValueAndFormat(symbolColumn, position);
        };
        let result = this.getters.evaluateCompiledFormula(
            column.computedBy.sheetId,
            formula,
            getSymbolValue
        );
        if (isMatrix(result)) {
            result = result[0][0];
        }
        this.computeCache[cacheKey] = result;
        return result;
    }

    _getListFormat(position, path, field) {
        const locale = this.getters.getLocale();
        switch (field?.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currency = this.getListCurrency(position, path, field.currency_field);
                if (!currency) {
                    return "#,##0.00";
                }
                return this.getters.computeFormatFromCurrency(currency);
            }
            case "date":
                return locale.dateFormat;
            case "datetime":
                return locale.dateFormat + " " + locale.timeFormat;
            case "char":
            case "text":
                return "@";
            default:
                return undefined;
        }
    }

    getListCurrency(position, path, currentFieldName) {
        return this.dataSource.getListCurrency(position, path, currentFieldName);
    }

    refresh() {
        this.computeCache = {};
        this.dataSource.load({ reload: true });
    }

    addDomain(domain) {
        this.dataSource.addDomain(domain);
    }

    updateDefinition(nextDefinition) {
        const currentCompute = this.definition.columns.map((col) => col.computedBy);
        const nextCompute = nextDefinition.columns.map((col) => col.computedBy);
        const computeChanged = !deepEquals(currentCompute, nextCompute);
        this.definition = nextDefinition;
        this.computeCache = {};
        this.dataSource.onDefinitionChange(nextDefinition, computeChanged);
    }

    invalidateCache() {
        this.computeCache = {};
    }
}
