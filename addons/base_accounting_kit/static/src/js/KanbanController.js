/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
const { useState } = owl;

class CustomKanbanController extends KanbanController {
    async setup(){
        super.setup()
        this.state = useState({
            selectedStLineId: null,
            linesWidgetData: null,
            moveLineData: null,
        });
        this.action = useService("action")
        this.orm = useService("orm")
        const o_bank_reconcile_status_buttons_aside_left = document.getElementsByClassName("o_bank_reconcile_status_buttons_aside_left")
    }

    async openRecord(record, mode) {
        this.state.moveLineData = null;
        this.state.viewID = await this.orm.call('res.config.settings', 'get_view_id', [])
        await this.mountStLine(record.resId);

        const statementRecord = document.querySelectorAll('.o_bank_reconcile_st_line_kanban_card');
        statementRecord.forEach(line => {
            line.addEventListener('click', async (event) => {
                // Remove 'div-added' class and its child divs from all elements
                statementRecord.forEach(item => {
                    item.classList.remove('div-added');
                    const childDiv = item.querySelector('.new-div');
                    if (childDiv) {
                        item.removeChild(childDiv);
                    }
                });
                // Add 'div-added' class and new div to the clicked record
                if (!line.classList.contains('div-added')) {
                    const newDiv = document.createElement('div');
                    newDiv.classList.add('new-div'); // Add a class to identify the new div
                    line.classList.add('div-added');
                    line.appendChild(newDiv);
                }
            });
        });
    }

    async mountStLine(stLineId){
        const currentStLineId = this.state.selectedStLineId;
        if (currentStLineId !== stLineId) {
            this.state.selectedStLineId = stLineId; // Update selected ST Line ID
            try {
                const data = await this.orm.call("account.bank.statement.line", "get_statement_line", [stLineId]);
                this.state.linesWidgetData = data;
            } catch (error) {
                console.error("Error fetching statement line data:", error);
            }
            try {
                const data = await this.orm.call('account.bank.statement.line', 'read', [[stLineId]], { fields: ['lines_widget_json'] });
                if (data && data.length > 0 && data[0].lines_widget_json) {
                    const parsedData = JSON.parse(data[0].lines_widget_json);
                    const moveIdMatch = parsedData.move_id.match(/\((\d+),\)/);
                    parsedData.numeric_move_id = moveIdMatch ? parseInt(moveIdMatch[1]) : null;
                    this.state.moveLineData = parsedData;
                } else {
                    console.warn("No lines_widget_json found for selected statement line.");
                }
            } catch (error) {
                console.error("Error reading statement line:", error);
            }
        }
    }

    get prepareFormPropsBankReconcile(){
        if (!this.state.selectedStLineId) {
            return null; // or some default props
        }
        return {
            type: "form",
            viewId: this.state.viewID,
            context: {
                default_st_line_id: this.state.selectedStLineId,
                default_lines_widget: this.state.linesWidgetData || null,
                default_move_line: this.state.moveLineData || null,
            },
            display: { controlPanel: false, noBreadcrumbs: true},
            mode: "edit",
            resModel: "account.bank.statement.line",
            resId: this.state.selectedStLineId,
        }
    }
}
CustomKanbanController.components = {
    ...CustomKanbanController.components, View }
CustomKanbanController.template = "base_accounting_kit.CustomKanbanView";

export class BankCustomKanbanRenderer extends KanbanRenderer {
    setup(){
        super.setup();
    }
}
export class BankReconcileKanbanRecord extends KanbanRecord {
    setup(){
        super.setup();
        this.state=useState({
            Statement_record:{}
        })
    }
}
BankReconcileKanbanRecord.template = "base_accounting_kit.BankReconcileKanbanRecord";

BankCustomKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: BankReconcileKanbanRecord,
}
BankCustomKanbanRenderer.template = "base_accounting_kit.BankRecKanbanRenderer";

export const customKanbanView = {
    ...kanbanView,
    Controller: CustomKanbanController,
    Renderer: BankCustomKanbanRenderer,
    searchMenuTypes: ["filter"],
};

// Register it to the views registry
registry.category("views").add("custom_kanban", customKanbanView);
