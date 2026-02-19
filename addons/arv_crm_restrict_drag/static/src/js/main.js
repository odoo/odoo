/** @odoo-module **/
const { Component, useState } = owl;
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

patch(KanbanRecord.prototype, "KanbanRecordDrag", {

    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, group, record } = this.props;
        const classes = ["o_kanban_record d-flex"];
        if (canResequence && this.props.group.aggregates.probability != 100) {
            classes.push("o_record_draggable");
        }
        if (forceGlobalClick || archInfo.openAction) {
            classes.push("oe_kanban_global_click");
        }
        if (group && record.model.hasProgressBars) {
            const progressBar = group.findProgressValueFromRecord(record);
            classes.push(`oe_kanban_card_${progressBar.color}`);
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(getColorClass(value));
        }
        if (!this.props.list.isGrouped) {
            classes.push("flex-grow-1 flex-md-shrink-1 flex-shrink-0");
        }
        return classes.join(" ");
    }

});