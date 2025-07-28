import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isCSSColor } from "@web/core/utils/colors";

export const DATASET_KEY_PREFIX = "chart_dataset_";

export function getColor(color, win, doc) {
    if (!color) {
        return "";
    }
    return isCSSColor(color)
        ? color
        : getCSSVariableValue(color, win.getComputedStyle(doc.documentElement));
}

export class ChartOption extends BaseOptionComponent {
    static template = "website.ChartOption";
    static selector = ".s_chart";
    static dependencies = ["chartOptionPlugin"];

    setup() {
        super.setup();

        // Here for compatibility with previous versions (< 18.3).
        this.env.getEditingElement().dataset.data = JSON.stringify(
            this.prepareData(this.env.getEditingElement())
        );

        this.state = useState({ currentCell: {} });

        this.domState = useDomState((editingElement) => ({
            data: this.getData(editingElement),
            isPieChart: this.isPieChart(editingElement),
        }));
        this.setDefaultState();
    }

    /**
     * Resets the current cell to the topleft cell
     * and sets the colorpicker labels based on chart type.
     */
    setDefaultState() {
        const { backgroundLabel, borderLabel } = this.getColorpickersLabels(
            this.domState.isPieChart
        );
        this.updateCurrentCell({
            backgroundLabel,
            borderLabel,
            datasetIndex: 0,
            dataIndex: 0,
        });
    }

    getData(editingElement) {
        return JSON.parse(editingElement.dataset.data);
    }
    /**
     * Parse the data from the DOM and make sure there are `key` properties
     * where needed by the component API.
     *
     * @param {HTMLElement} editingElement
     * @returns {Object}
     */
    prepareData(editingElement) {
        const data = this.getData(editingElement);
        data.datasets = data.datasets.map((dataset) => {
            if (dataset.key) {
                return dataset;
            }
            return {
                ...dataset,
                key: DATASET_KEY_PREFIX + Date.now(),
            };
        });
        return data;
    }
    isPieChart(editingElement) {
        const isPieChart = this.dependencies.chartOptionPlugin.isPieChart(editingElement);
        if (!this.domState || this.domState.isPieChart !== isPieChart) {
            // Pie charts set color on a data cell basis, whereas the
            // other ones set it on a dataset basis
            const { backgroundLabel, borderLabel } = this.getColorpickersLabels(isPieChart);
            this.updateCurrentCell({ backgroundLabel, borderLabel });
        }
        return isPieChart;
    }
    getColorpickersLabels(isPieChart) {
        const backgroundLabel = isPieChart ? _t("Data Color") : _t("Dataset Color");
        const borderLabel = isPieChart ? _t("Data Border") : _t("Dataset Border");
        return { backgroundLabel, borderLabel };
    }
    getColor(color) {
        return getColor(color, this.window, this.document);
    }
    /**
     * Retrieve the colors already in use in the chart.
     *
     * @returns {Set} set of hexadecimal colors
     */
    getColorPalette() {
        const editingElement = this.env.getEditingElement();
        const data = this.getData(editingElement);
        const colorSet = new Set();
        for (const dataset of data.datasets) {
            if (this.isPieChart(editingElement)) {
                dataset.backgroundColor.forEach((color) => colorSet.add(this.getColor(color)));
                dataset.borderColor.forEach((color) => colorSet.add(this.getColor(color)));
            } else {
                colorSet.add(this.getColor(dataset.backgroundColor));
                colorSet.add(this.getColor(dataset.borderColor));
            }
        }
        colorSet.delete(""); // No color, remove to avoid bugs.
        return colorSet;
    }

    /**
     * @param {Object} updatedCellInfo
     * @param {Number} [updatedCellInfo.dataIndex]
     * @param {Number} [updatedCellInfo.datasetIndex]
     * @param {String} [updatedCellInfo.backgroundLabel]
     * @param {String} [updatedCellInfo.borderLabel]
     */
    updateCurrentCell(updatedCellInfo) {
        for (const key in updatedCellInfo) {
            this.state.currentCell[key] = updatedCellInfo[key];
        }
    }

    /**
     * Extracts information about the table cell from a table event.
     *
     * @param {Event} ev - The event triggered on the table.
     * @returns {Object} Containing:
     *   - cellEl: The cell element (td or th) that was interacted.
     *   - cellSectionEl: The section element (THEAD or TBODY) containing the cell.
     *   - datasetIndex: The column index of the cell (excluding label column).
     *   - dataIndex: The row index of the cell (only for TBODY rows).
     */
    getCellInfo(ev) {
        const cellEl = ev.target.closest("td, th");
        if (cellEl) {
            const cellRowEl = cellEl.parentElement;
            const cellSectionEl = cellRowEl.parentElement;
            const datasetIndex = [...cellRowEl.children].indexOf(cellEl) - 1;
            let dataIndex;
            if (cellSectionEl.tagName === "TBODY") {
                dataIndex = [...cellSectionEl.children].indexOf(cellRowEl);
            }
            return { cellEl, cellSectionEl, datasetIndex, dataIndex };
        }
        return {};
    }

    isTableButton(target) {
        return !!target.closest(
            ".o_builder_matrix_remove_row, .add_row, .o_builder_matrix_remove_col, .add_column"
        );
    }
    /**
     * Store in the state the coords of the cell that is currently focused.
     *
     * @param {Event} ev
     */
    onTableFocusin(ev) {
        this.onTableMouseover(ev);
        this.handleCellFocus(ev);
    }
    /**
     * Used to display the corresponding colorpickers.
     *
     * @param {Event} ev
     */
    handleCellFocus(ev) {
        if (this.isTableButton(ev.target)) {
            return;
        }
        const { cellEl, cellSectionEl, datasetIndex, dataIndex } = this.getCellInfo(ev);
        if (!cellEl) {
            return;
        }
        const cellRowEl = cellEl.parentElement;
        if (cellSectionEl.tagName === "THEAD" && datasetIndex !== -1) {
            this.updateCurrentCell({
                datasetIndex: this.domState.isPieChart ? null : datasetIndex,
                dataIndex: this.domState.isPieChart ? null : 0,
            });
        }
        // click on a table inner cell
        else if (datasetIndex !== -1 && datasetIndex !== cellRowEl.children.length - 2) {
            this.updateCurrentCell({ datasetIndex, dataIndex });
        }
    }
    /**
     * Handles the click on table buttons.
     *
     * @param {Event} ev - The event triggered on the table cell button.
     */
    onButtonCellClick(ev) {
        if (!this.isTableButton(ev.target)) {
            return;
        }
        const { cellEl, cellSectionEl, datasetIndex, dataIndex } = this.getCellInfo(ev);
        const isColumnButton = dataIndex === cellSectionEl.children.length - 1;
        const isRowButton = datasetIndex === cellEl.parentElement.children.length - 2;

        if (isColumnButton) {
            if (ev.target.classList.contains("add_row")) {
                this.updateCurrentCell({ datasetIndex: 0, dataIndex });
            }
            // if we delete a column with the current cell
            else if (datasetIndex === this.state.currentCell.datasetIndex) {
                this.setDefaultState();
            } else if (datasetIndex < this.state.currentCell.datasetIndex) {
                this.updateCurrentCell({ datasetIndex: this.state.currentCell.datasetIndex - 1 });
            }
            return;
        }

        if (isRowButton) {
            if (ev.target.classList.contains("add_column")) {
                this.updateCurrentCell({ datasetIndex, dataIndex: 0 });
            }
            // if we delete a row with the current cell
            else if (dataIndex === this.state.currentCell.dataIndex) {
                this.setDefaultState();
            } else if (dataIndex < this.state.currentCell.dataIndex) {
                this.updateCurrentCell({ dataIndex: this.state.currentCell.dataIndex - 1 });
            }
        }
    }

    /**
     * Handles the click on the THEAD (Dataset Labels).
     *
     * @param {Event} ev - The event triggered on the thead cell.
     */
    onDatasetLabelClick(ev) {
        const { datasetIndex } = this.getCellInfo(ev);
        this.updateCurrentCell({
            datasetIndex: this.domState.isPieChart ? null : datasetIndex,
            dataIndex: this.domState.isPieChart ? null : 0,
        });
    }

    onTableMouseoutOrFocusout(ev) {
        ev.currentTarget
            .querySelector(".o_builder_matrix_remove_col:not(.visually-hidden-focusable)")
            ?.classList.add("visually-hidden-focusable");
        ev.currentTarget
            .querySelector(".o_builder_matrix_remove_row:not(.visually-hidden-focusable)")
            ?.classList.add("visually-hidden-focusable");
    }
    /**
     * Compute the column that is hovered and show the remove_col button.
     *
     * @param {Event} ev
     */
    onTableMouseover(ev) {
        ev.stopPropagation();
        if (ev.target === ev.currentTarget) {
            return;
        }
        const tableEl = ev.currentTarget;
        const cellEl = ev.target.closest("td, th");
        const rowEl = cellEl.closest("tr");
        const columnIndex = [...rowEl.children].indexOf(cellEl);

        // Remove column: allowed if more than 1 dataset & on dataset columns (
        // not on the labels column nor the buttons column).
        if (
            rowEl.children.length > 3 && // label + value + button
            columnIndex > 0 &&
            columnIndex < rowEl.children.length - 1
        ) {
            tableEl
                .querySelectorAll(".o_builder_matrix_remove_col")
                [columnIndex - 1].classList.remove("visually-hidden-focusable");
        }

        // Remove row: allowed if more than 1 label & on actual data rows (not
        // on the header row nor the buttons row).
        if (
            rowEl.parentElement.children.length > 2 && // value + button
            cellEl.closest("tbody") &&
            rowEl.nextElementSibling
        ) {
            rowEl
                .querySelector(".o_builder_matrix_remove_row")
                .classList.remove("visually-hidden-focusable");
        }
    }
}
