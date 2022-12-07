odoo.define('website.s_chart_options', function (require) {
'use strict';

var core = require('web.core');
const {ColorpickerWidget} = require('web.Colorpicker');
var options = require('web_editor.snippets.options');
const weUtils = require('web_editor.utils');

var _t = core._t;

options.registry.InnerChart = options.Class.extend({
    custom_events: _.extend({}, options.Class.prototype.custom_events, {
        'get_custom_colors': '_onGetCustomColors',
    }),
    events: _.extend({}, options.Class.prototype.events, {
        'click we-button.add_column': '_onAddColumnClick',
        'click we-button.add_row': '_onAddRowClick',
        'click we-button.o_we_matrix_remove_col': '_onRemoveColumnClick',
        'click we-button.o_we_matrix_remove_row': '_onRemoveRowClick',
        'blur we-matrix input': '_onMatrixInputFocusOut',
        'focus we-matrix input': '_onMatrixInputFocus',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.themeArray = ['o-color-1', 'o-color-2', 'o-color-3', 'o-color-4', 'o-color-5'];
        this.style = window.getComputedStyle(document.documentElement);
    },
    /**
     * @override
     */
    start: function () {
        this.backSelectEl = this.el.querySelector('[data-name="chart_bg_color_opt"]');
        this.borderSelectEl = this.el.querySelector('[data-name="chart_border_color_opt"]');

        // Build matrix content
        this.tableEl = this.el.querySelector('we-matrix table');
        const data = JSON.parse(this.$target[0].dataset.data);
        data.labels.forEach(el => {
            this._addRow(el);
        });
        data.datasets.forEach((el, i) => {
            if (this._isPieChart()) {
                // Add header colors in case the user changes the type of graph
                const headerBackgroundColor = this.themeArray[i] || this._randomColor();
                const headerBorderColor = this.themeArray[i] || this._randomColor();
                this._addColumn(el.label, el.data, headerBackgroundColor, headerBorderColor, el.backgroundColor, el.borderColor);
            } else {
                this._addColumn(el.label, el.data, el.backgroundColor, el.borderColor);
            }
        });
        this._displayRemoveColButton();
        this._displayRemoveRowButton();
        this._setDefaultSelectedInput();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    updateUI: async function () {
        // Selected input might not be in dom anymore if col/row removed
        // Done before _super because _computeWidgetState of colorChange
        if (!this.lastEditableSelectedInput.closest('table') || this.colorPaletteSelectedInput && !this.colorPaletteSelectedInput.closest('table')) {
            this._setDefaultSelectedInput();
        }

        await this._super(...arguments);

        this.backSelectEl.querySelector('we-title').textContent = this._isPieChart() ? _t("Data Color") : _t("Dataset Color");
        this.borderSelectEl.querySelector('we-title').textContent = this._isPieChart() ? _t("Data Border") : _t("Dataset Border");

        // Dataset/Cell color
        this.tableEl.querySelectorAll('input').forEach(el => el.style.border = '');
        const selector = this._isPieChart() ? 'td input' : 'tr:first-child input';
        this.tableEl.querySelectorAll(selector).forEach(el => {
            const color = el.dataset.backgroundColor || el.dataset.borderColor;
            if (color) {
                el.style.border = '2px solid';
                el.style.borderColor = ColorpickerWidget.isCSSColor(color) ? color : weUtils.getCSSVariableValue(color, this.style);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Set the color on the selected input.
     */
    colorChange: async function (previewMode, widgetValue, params) {
        if (widgetValue) {
            this.colorPaletteSelectedInput.dataset[params.attributeName] = widgetValue;
        } else {
            delete this.colorPaletteSelectedInput.dataset[params.attributeName];
        }
        await this._reloadGraph();
        // To focus back the input that is edited we have to wait for the color
        // picker to be fully reloaded.
        await new Promise(resolve => setTimeout(() => {
            this.lastEditableSelectedInput.focus();
            resolve();
        }));
    },
    /**
     * @override
     */
    selectDataAttribute: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);
        // Data might change if going from or to a pieChart.
        if (params.attributeName === 'type') {
            this._setDefaultSelectedInput();
            await this._reloadGraph();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'colorChange') {
            return this.colorPaletteSelectedInput && this.colorPaletteSelectedInput.dataset[params.attributeName] || '';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility: function (widgetName, params) {
        switch (widgetName) {
            case 'stacked_chart_opt': {
                return this._getColumnCount() > 1;
            }
            case 'chart_bg_color_opt':
            case 'chart_border_color_opt': {
                return !!this.colorPaletteSelectedInput;
            }
        }
        return this._super(...arguments);
    },
    /**
     * Sets and reloads the data on the canvas if it has changed.
     * Used in matrix related method.
     *
     * @private
     */
    _reloadGraph: async function () {
        const jsonValue = this._matrixToChartData();
        if (this.$target[0].dataset.data !== jsonValue) {
            this.$target[0].dataset.data = jsonValue;
            await this._refreshPublicWidgets();
        }
    },
    /**
     * Return a stringifyed chart.js data object from the matrix
     * Pie charts have one color per data while other charts have one color per dataset.
     *
     * @private
     */
    _matrixToChartData: function () {
        const data = {
            labels: [],
            datasets: [],
        };
        this.tableEl.querySelectorAll('tr:first-child input').forEach(el => {
            data.datasets.push({
                label: el.value || '',
                data: [],
                backgroundColor: this._isPieChart() ? [] : el.dataset.backgroundColor || '',
                borderColor: this._isPieChart() ? [] : el.dataset.borderColor || '',
            });
        });
        this.tableEl.querySelectorAll('tr:not(:first-child):not(:last-child)').forEach((el) => {
            const title = el.querySelector('th input').value || '';
            data.labels.push(title);
            el.querySelectorAll('td input').forEach((el, i) => {
                data.datasets[i].data.push(el.value || 0);
                if (this._isPieChart()) {
                    data.datasets[i].backgroundColor.push(el.dataset.backgroundColor || '');
                    data.datasets[i].borderColor.push(el.dataset.borderColor || '');
                }
            });
        });
        return JSON.stringify(data);
    },
    /**
     * Return a td containing a we-button with minus icon
     *
     * @param  {...string} classes Classes to add to the we-button
     * @returns {HTMLElement}
     */
    _makeDeleteButton: function (...classes) {
        const rmbuttonEl = options.buildElement('we-button', null, {
            classes: ['o_we_text_danger', 'o_we_link', 'fa', 'fa-fw', 'fa-minus', ...classes],
        });
        rmbuttonEl.title = classes.includes('o_we_matrix_remove_col') ? _t("Remove Serie") : _t("Remove Row");
        const newEl = document.createElement('td');
        newEl.appendChild(rmbuttonEl);
        return newEl;
    },
    /**
     * Add a column to the matrix
     * The th (dataset label) of a column hold the colors for the entire dataset if the graph is not a pie chart
     * If the graph is a pie chart the color of the td (data) are used.
     *
     * @private
     * @param {String} title The title of the column
     * @param {Array} values The values of the column input
     * @param {String} heardeBackgroundColor The background color of the dataset
     * @param {String} headerBorderColor The border color of the dataset
     * @param {string[]} cellBackgroundColors The background colors of the datas inputs, random color if missing
     * @param {string[]} cellBorderColors The border color of the datas inputs, no color if missing
     */
    _addColumn: function (title, values, heardeBackgroundColor, headerBorderColor, cellBackgroundColors = [], cellBorderColors = []) {
        const firstRow = this.tableEl.querySelector('tr:first-child');
        const headerInput = this._makeCell('th', title, heardeBackgroundColor, headerBorderColor);
        firstRow.insertBefore(headerInput, firstRow.lastElementChild);

        this.tableEl.querySelectorAll('tr:not(:first-child):not(:last-child)').forEach((el, i) => {
            const newCell = this._makeCell('td', values ? values[i] : null, cellBackgroundColors[i] || this._randomColor(), cellBorderColors[i - 1]);
            el.insertBefore(newCell, el.lastElementChild);
        });

        const lastRow = this.tableEl.querySelector('tr:last-child');
        const removeButton = this._makeDeleteButton('o_we_matrix_remove_col');
        lastRow.appendChild(removeButton);
    },
    /**
     * Add a row to the matrix
     * The background color of the datas are random
     *
     * @private
     * @param {String} tilte The title of the row
     */
    _addRow: function (tilte) {
        const trEl = document.createElement('tr');
        trEl.appendChild(this._makeCell('th', tilte));
        this.tableEl.querySelectorAll('tr:first-child input').forEach(() => {
            trEl.appendChild(this._makeCell('td', null, this._randomColor()));
        });
        trEl.appendChild(this._makeDeleteButton('o_we_matrix_remove_row'));
        const tbody = this.tableEl.querySelector('tbody');
        tbody.insertBefore(trEl, tbody.lastElementChild);
    },
    /**
     * @private
     * @param {string} tag tag of the HTML Element (td/th)
     * @param {string} value The current value of the cell input
     * @param {string} backgroundColor The background Color of the data on the graph
     * @param {string} borderColor The border Color of the the data on the graph
     * @returns {HTMLElement}
     */
    _makeCell: function (tag, value, backgroundColor, borderColor) {
        const newEl = document.createElement(tag);
        const contentEl = document.createElement('input');
        contentEl.type = 'text';
        contentEl.value = value || '';
        if (backgroundColor) {
            contentEl.dataset.backgroundColor = backgroundColor;
        }
        if (borderColor) {
            contentEl.dataset.borderColor = borderColor;
        }
        newEl.appendChild(contentEl);
        return newEl;
    },
    /**
     * Display the remove button coresponding to the colIndex
     *
     * @private
     * @param {Int} colIndex Can be undefined, if so the last remove button of the column will be shown
     */
    _displayRemoveColButton: function (colIndex) {
        if (this._getColumnCount() > 1) {
            this._displayRemoveButton(colIndex, 'o_we_matrix_remove_col');
        }
    },
    /**
     * Display the remove button coresponding to the rowIndex
     *
     * @private
     * @param {Int} rowIndex Can be undefined, if so the last remove button of the row will be shown
     */
    _displayRemoveRowButton: function (rowIndex) {
        //Nbr of row minus header and button
        const rowCount = this.tableEl.rows.length - 2;
        if (rowCount > 1) {
            this._displayRemoveButton(rowIndex, 'o_we_matrix_remove_row');
        }
    },
    /**
     * @private
     * @param {Int} tdIndex Can be undefined, if so the last remove button will be shown
     * @param {String} btnClass Either o_we_matrix_remove_col or o_we_matrix_remove_row
     */
    _displayRemoveButton: function (tdIndex, btnClass) {
        const removeBtn = this.tableEl.querySelectorAll(`td we-button.${btnClass}`);
        removeBtn.forEach(el => el.style.display = ''); //hide all
        const index = tdIndex < removeBtn.length ? tdIndex : removeBtn.length - 1;
        removeBtn[index].style.display = 'inline-block';
    },
    /**
     * @private
     * @return {boolean}
     */
    _isPieChart: function () {
        return ['pie', 'doughnut'].includes(this.$target[0].dataset.type);
    },
    /**
     * Return the number of column minus header and button
     * @private
     * @return {integer}
     */
    _getColumnCount: function () {
        return this.tableEl.rows[0].cells.length - 2;
    },
    /**
     * Select the first data input
     *
     * @private
     */
    _setDefaultSelectedInput: function () {
        this.lastEditableSelectedInput = this.tableEl.querySelector('td input');
        if (this._isPieChart()) {
            this.colorPaletteSelectedInput = this.lastEditableSelectedInput;
        } else {
            this.colorPaletteSelectedInput = this.tableEl.querySelector('th input');
        }
    },
    /**
     * Return a random hexadecimal color.
     *
     * @private
     * @return {string}
     */
    _randomColor: function () {
        return '#' + ('00000' + (Math.random() * (1 << 24) | 0).toString(16)).slice(-6).toUpperCase();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Used by colorPalette to retrieve the custom colors used on the chart
     * Make an array with all the custom colors used on the chart
     * and apply it to the onSuccess method provided by the trigger_up.
     *
     * @private
     */
    _onGetCustomColors: function (ev) {
        const data = JSON.parse(this.$target[0].dataset.data || '');
        let customColors = [];
        data.datasets.forEach(el => {
            if (this._isPieChart()) {
                customColors = customColors.concat(el.backgroundColor).concat(el.borderColor);
            } else {
                customColors.push(el.backgroundColor);
                customColors.push(el.borderColor);
            }
        });
        customColors = customColors.filter((el, i, array) => {
            return !weUtils.getCSSVariableValue(el, this.style) && array.indexOf(el) === i && el !== ''; // unique non class not transparent
        });
        ev.data.onSuccess(customColors);
    },
    /**
     * Add a row at the end of the matrix and display it's remove button
     * Choose the color of the column from the theme array or a random color if they are already used
     *
     * @private
     */
    _onAddColumnClick: function () {
        const usedColor = Array.from(this.tableEl.querySelectorAll('tr:first-child input')).map(el => el.dataset.backgroundColor);
        const color = this.themeArray.filter(el => !usedColor.includes(el))[0] || this._randomColor();
        this._addColumn(null, null, color, color);
        this._reloadGraph().then(() => {
            this._displayRemoveColButton();
            this.updateUI();
        });
    },
    /**
     * Add a column at the end of the matrix and display it's remove button
     *
     * @private
     */
    _onAddRowClick: function () {
        this._addRow();
        this._reloadGraph().then(() => {
            this._displayRemoveRowButton();
            this.updateUI();
        });
    },
    /**
     * Remove the column and show the remove button of the next column or the last if no next.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveColumnClick: function (ev) {
        const cell = ev.currentTarget.parentElement;
        const cellIndex = cell.cellIndex;
        this.tableEl.querySelectorAll('tr').forEach((el) => {
            el.children[cellIndex].remove();
        });
        this._displayRemoveColButton(cellIndex - 1);
        this._reloadGraph().then(() => {
            this.updateUI();
        });
    },
    /**
     * Remove the row and show the remove button of the next row or the last if no next.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveRowClick: function (ev) {
        const row = ev.currentTarget.parentElement.parentElement;
        const rowIndex = row.rowIndex;
        row.remove();
        this._displayRemoveRowButton(rowIndex - 1);
        this._reloadGraph().then(() => {
            this.updateUI();
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMatrixInputFocusOut: function (ev) {
        this._reloadGraph();
    },
    /**
     * Set the selected cell/header and display the related remove button
     *
     * @private
     * @param {Event} ev
     */
    _onMatrixInputFocus: function (ev) {
        this.lastEditableSelectedInput = ev.target;
        const col = ev.target.parentElement.cellIndex;
        const row = ev.target.parentElement.parentElement.rowIndex;
        if (this._isPieChart()) {
            this.colorPaletteSelectedInput = ev.target.parentNode.tagName === 'TD' ? ev.target : null;
        } else {
            this.colorPaletteSelectedInput = this.tableEl.querySelector(`tr:first-child th:nth-of-type(${col + 1}) input`);
        }
        if (col > 0) {
            this._displayRemoveColButton(col - 1);
        }
        if (row > 0) {
            this._displayRemoveRowButton(row - 1);
        }
        this.updateUI();
    },
});
});
