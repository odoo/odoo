import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export const DATASET_KEY_PREFIX = "chart_dataset_";

export class ChartOption extends BaseOptionComponent {
    static template = "website.ChartOption";
    static props = {
        isPieChart: Function,
        getColor: Function,
    };

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
        const isPieChart = this.props.isPieChart(editingElement);
        if (!this.domState || this.domState.isPieChart !== isPieChart) {
            // Pie charts set color on a data cell basis, whereas the
            // other ones set it on a dataset basis. Just reset the
            // current cell to avoid bugs.
            this.state.currentCell = {};
        }
        return isPieChart;
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
                dataset.backgroundColor.forEach((color) =>
                    colorSet.add(this.props.getColor(color))
                );
                dataset.borderColor.forEach((color) => colorSet.add(this.props.getColor(color)));
            } else {
                colorSet.add(this.props.getColor(dataset.backgroundColor));
                colorSet.add(this.props.getColor(dataset.borderColor));
            }
        }
        colorSet.delete(""); // No color, remove to avoid bugs.
        return colorSet;
    }
    /**
     * Store in the state the coords of the cell that is currently focused.
     * (Used to display the corresponding colorpickers.)
     *
     * @param {Event} ev
     */
    onTableFocusin(ev) {
        this.onTableMouseover(ev);
        ev.currentTarget
            .querySelector(".o_builder_matrix_selected_cell")
            ?.classList.remove("o_builder_matrix_selected_cell");
        const cellEl = ev.target.closest("td, th");
        const cellSectionEl = cellEl.parentElement.parentElement;
        const datasetIndex = [...cellEl.parentElement.children].indexOf(cellEl) - 1;
        if (datasetIndex === -1 || datasetIndex === cellEl.parentElement.children.length - 2) {
            // Dataset label cell or remove row button: no color to show.
            this.state.currentCell = {};
            return;
        }
        let dataIndex;
        if (cellSectionEl.tagName === "TBODY") {
            dataIndex = [...cellSectionEl.children].indexOf(cellEl.parentElement);
            if (dataIndex === cellSectionEl.children.length - 1) {
                // Remove column button: no color to show.
                this.state.currentCell = {};
                return;
            }
        }

        let backgroundLabel = _t("Dataset Color");
        let borderLabel = _t("Dataset Border");
        if (this.domState.isPieChart) {
            backgroundLabel = _t("Data Color");
            borderLabel = _t("Data Border");
            if (cellSectionEl.tagName === "THEAD") {
                this.state.currentCell = {};
                return;
            }
        }
        cellEl.classList.add("o_builder_matrix_selected_cell");
        this.state.currentCell = { datasetIndex, dataIndex, backgroundLabel, borderLabel };
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
