/** @odoo-module */

import {ListRenderer} from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";

export const RangeListSelector = {
    setup() {
        this._super(...arguments);
        this.range_history = [];
    },
    _getRangeSelection() {
        var self = this;
        // Get start and end
        var start = null,
            end = null;
        $(".o_list_record_selector input").each(function (i, el) {
            var id = $(el).closest("tr").data("id");
            var checked = self.range_history.indexOf(id) !== -1;
            if (checked && $(this).is(":checked")) {
                if (start === null) {
                    start = i;
                } else {
                    end = i;
                }
            }
        });
        var new_range = this._getSelectionByRange(start, end);

        var current_selection = [];
        current_selection = _.uniq(current_selection.concat(new_range));
        return current_selection;
    },
    _getSelectionByRange(start, end) {
        var result = [];
        $(".o_list_record_selector input")
            .closest("tr")
            .each(function (i, el) {
                var record_id = $(el).data("id");
                if (start !== null && end !== null && i >= start && i <= end) {
                    result.push(record_id);
                } else if (start !== null && end === null && start === i) {
                    result.push(record_id);
                }
            });
        return result;
    },
    _pushRangeHistory(id) {
        if (this.range_history !== undefined) {
            if (this.range_history.length === 2) {
                this.range_history = [];
            }
        }
        this.range_history.push(id);
    },
    _deselectTable() {
        // This is needed because the checkboxes are not real checkboxes.
        window.getSelection().removeAllRanges();
    },
    _onClickSelectRecord(record, ev) {
        const el = $(ev.currentTarget);
        if (el.find("input").prop("checked")) {
            this._pushRangeHistory(el.closest("tr").data("id"));
        }
        if (ev.shiftKey) {
            // Get selection
            var selection = this._getRangeSelection();
            var $rows = $("td.o_list_record_selector input").closest("tr");
            $rows.each(function () {
                var record_id = $(this).data("id");
                if (selection.indexOf(record_id) !== -1) {
                    $(this)
                        .find("td.o_list_record_selector input")
                        .prop("checked", true);
                }
            });
            // Update selection internally
            this.checkBoxSelections(selection);
            this._deselectTable();
        }
    },
    checkBoxSelections(selection) {
        const record = this.props.list.records;
        for (const line in record) {
            for (const id in selection) {
                if (selection[selection.length - 1] === selection[id]) {
                    continue;
                }
                if (selection[id] === record[line].id) {
                    record[line].selected = true;
                    record[line].model.trigger("update");
                    continue;
                }
            }
        }
    },
};
patch(
    ListRenderer.prototype,
    "web_listview_range_select.WebListviewRangeSelect",
    RangeListSelector
);
