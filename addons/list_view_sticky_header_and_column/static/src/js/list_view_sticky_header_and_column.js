/** @odoo-module **/
/**
 * This file will used to stick the selected header and column in  the list view
 */
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
patch(ListRenderer.prototype, "my_list_view_patch", {
    /**
     * super the setup function
     */
    setup() {
        this._super.apply();
    },
    /**
     * function defining the button having t-on-click _onClick
     */
    _onClickIcon(ev, record) {
        ev.preventDefault();
        ev.stopPropagation()
        const $clickedHeader = $(ev.currentTarget).closest('th');
        const columnIndex = $clickedHeader.index();
        $(this.__owl__.bdom.parentEl.querySelectorAll('.sticky-column')).removeClass('sticky-column');
        $(this.__owl__.bdom.parentEl.querySelectorAll('.clicked-header')).removeClass('clicked-header');
        $clickedHeader.addClass('clicked-header');
        const $tableHeaders = $(this.__owl__.bdom.parentEl.querySelectorAll('.o_list_table th'));
        const $tableRows = $(this.__owl__.bdom.parentEl.querySelectorAll('.o_list_table tr'));
        const $tfootRow = $(this.__owl__.bdom.parentEl.querySelectorAll('.o_list_table tfoot tr')[0].children);
        const $selectedFooterCells = $tfootRow.filter(`td:nth-child(-n+${columnIndex + 1})`);
        $selectedFooterCells.addClass('sticky-column');
        const $selectedColumns = $(this.__owl__.bdom.parentEl.querySelectorAll(`.o_data_row td:nth-child(-n+${columnIndex + 1})`));
        const $selectedHeaderCells = $tableHeaders.filter(`th:nth-child(-n+${columnIndex + 1})`);
        $tableHeaders.removeClass('sticky-column').css('left', '');
        $(this.__owl__.bdom.parentEl.querySelectorAll('.o_data_row td')).removeClass('sticky-column').css('left', '');
        $selectedColumns.addClass('sticky-column');
        $selectedHeaderCells.addClass('sticky-column');
        $tableHeaders.filter('.sticky-column').css('top', '0');
        const $targetColumn = $selectedColumns.eq(columnIndex);
        const targetLeftPosition = $targetColumn.position().left;
        const columnsToAdjust = columnIndex + 1;
        $tableRows.each(function (index, row) {
            const $headerCells = $(row).find('th');
            const $rowCells = $(row).find('td');
            for (let i = 0; i < columnsToAdjust; i++) {
                if ($headerCells.eq(i).length > 0) {
                    $headerCells.eq(i).css('left', `${$headerCells.eq(i).position().left}px`);
                }
                if ($rowCells.eq(i).length > 0) {
                    $rowCells.eq(i).css('left', `${$rowCells.eq(i).position().left}px`);
                }
            }
        });
    },
    /**
     * super onClickSortColumn function and remove the icon and element having the class sticky-column
     */
    onClickSortColumn(column) {
        this._super(...arguments);
        $(this.__owl__.bdom.parentEl.querySelectorAll('.sticky-column')).removeClass('sticky-column');
        $(this.__owl__.bdom.parentEl.querySelectorAll('.clicked-header')).removeClass('clicked-header');
        const $tableHeaders = $(this.__owl__.bdom.parentEl.querySelectorAll('.o_list_table th'));
        $tableHeaders.removeClass('sticky-column').css('left', '');
    }
});
