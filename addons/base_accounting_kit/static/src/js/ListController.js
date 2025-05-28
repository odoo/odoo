/** @odoo-module **/
import { registry } from '@web/core/registry';
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { useState, useRef } from "@odoo/owl";
import { useListener, useService} from "@web/core/utils/hooks";
export class AccountMoveLineListController extends ListController {
     constructor() {
        super(...arguments);
        this.resIdList = [];
     }
     setup(){
         super.setup();
         this.state = useState({ selectedRecordId: null ,
                                 selectedRecordIds: [],});
         this.action = useService("action")
         this.orm = useService("orm")
     }
     async openRecord(record) {
        const kanban_row = this.__owl__.bdom.parentEl.ownerDocument.querySelector(`tr[data-id]`);
        const data_id = parseInt(kanban_row.getAttribute('data-id'))
        var data = await this.orm.call('account.bank.statement.line',
            'update_match_row_data',
            [record.resId])
        await this.orm.call('account.bank.statement.line', 'write', [[data_id], { lines_widget_json: JSON.stringify(data) }]);
        const rowSelector = this.__owl__.bdom.parentEl.querySelector(`tr[data-id='${record.id}']`)
         if (!record.clickCount) {
            record.clickCount = true
            rowSelector.style.backgroundColor = "#d1ecf1";
         } else {
            // Set the default background color here
            record.clickCount = false;
            rowSelector.style.backgroundColor = "white";
         }

        const currencySymbol = await this.orm.call('res.currency', 'read',[record.data.currency_id[0]])
        const mainKanbanDiv = this.__owl__.bdom.parentEl.ownerDocument.querySelector('#base_accounting_reconcile')
        const existingRow = this.__owl__.bdom.parentEl.ownerDocument.querySelector(`tr[data-resId="${record.resId}"]`)
        const stateLineRow = this.__owl__.bdom.parentEl.ownerDocument.querySelector('.statement_row')
        if (stateLineRow){
            const dataIdValue = stateLineRow.getAttribute('data-id');
            if(dataIdValue == record.resId){
                mainKanbanDiv.removeChild(stateLineRow);
            }
        }
        if (existingRow) {
            mainKanbanDiv.removeChild(existingRow);
        } else {
            // If the row doesn't exist, create and add it
            const dateObject = new Date(record.data.date);
            const year = dateObject.getFullYear();
            const month = String(dateObject.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
            const day = String(dateObject.getDate()).padStart(2, '0');
            const formattedDate = `${year}-${month}-${day}`;
            let amount = parseFloat(record.data.amount_residual);
            let debitColumn = '';
            let creditColumn = '';
            let partnerName = '';
            let moveId = '';

            // Check if partner_id exists and is not empty
            if (record.data.partner_id && record.data.partner_id[1]) {
                partnerName = record.data.partner_id[1];
            }
            if (record.data.move_id && record.data.move_id[1]) {
                moveId = `<br/><span id="moveLine" style="font-size: 12px; font-style: italic;font-weight: normal;color: #01666b;cursor: pointer;" data-moveId="${record.data.move_id[0]}">${record.data.move_id[1]}</span>`;
            }


            if (amount < 0) {
                debitColumn = `<td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${currencySymbol[0].symbol} ${-amount}</td>`;
            } else {
                creditColumn = `<td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${currencySymbol[0].symbol} ${amount}</td>`;
            }

            const newRow = document.createElement('tr');
            newRow.setAttribute('data-resId', record.resId); // Set a unique identifier for the row
            if (debitColumn !== '') {
                newRow.innerHTML = `<td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${record.data.account_id[1]}
                                    ${moveId}<span style="font-size: 12px;font-style: italic;font-weight: normal;"> : ${record.data.name}</span></td>
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${partnerName}</td>
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${formattedDate}</td>
                                    ${debitColumn}
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;"> </td>
                                    <td class="o_list_remove_record">
                                    <button class="btn fa fa-trash-o" data-resId="${record.resId}"/>
                                    </td>`;

            } else if (creditColumn !== '') {
                newRow.innerHTML = `<td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${record.data.account_id[1]}
                                    ${moveId}<span style="font-size: 12px;font-style: italic;font-weight: normal;"> : ${record.data.name}</span></td>
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${partnerName}</td>
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;">${formattedDate}</td>
                                    <td style="font-weight: bold; display: table-cell; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: top;"> </td>
                                    ${creditColumn}
                                    <td class="o_list_remove_record">
                                    <button class="btn fa fa-trash-o" data-resId="${record.resId}"/>
                                    </td>`;
            }
            newRow.addEventListener('click', async () => {
                const allRows = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('tr[data-resId]');
                allRows.forEach(row => {
                    row.classList.remove('selected-row');
                });
                 newRow.classList.add('selected-row');
                 if (record.resId){
                    const manualOpsTab = this.__owl__.bdom.parentEl.ownerDocument.querySelector('[name="manual_operations_tab"]');
                    if (manualOpsTab) {
                        manualOpsTab.click();
                        const accountField = this.__owl__.bdom.parentEl.ownerDocument.querySelector('[name="account_id"]');
                        accountField.value = record.data.account_id[1];
                    }
                 }
            });
            // Append the new row to the mainKanbanDiv
            mainKanbanDiv.appendChild(newRow);
            const deleteButtons = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('.fa-trash-o');
            deleteButtons.forEach(button => {
                button.addEventListener('click', async (event) => {
                    const resId = event.target.getAttribute('data-resId');
                    await this.removeRecord(resId);
                });
            });
            const moveLine = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('#moveLine');
            moveLine.forEach(line => {
                line.addEventListener('click',async (event) => {
                    const moveId = event.target.getAttribute('data-moveId');
                    await this.ShowMoveForm(moveId);
                });
            });
        }
        this.updateResIdList();
    }
    async removeRecord(resId){
        const mainKanbanDiv = this.__owl__.bdom.parentEl.ownerDocument.querySelector('#base_accounting_reconcile');
        const rowToRemove = this.__owl__.bdom.parentEl.ownerDocument.querySelector(`tr[data-resId="${resId}"]`);
        if (rowToRemove) {
            mainKanbanDiv.removeChild(rowToRemove);
            this.updateResIdList();
        }
    }
    async ShowMoveForm(moveId) {
    // Convert moveId from string to integer
        const moveIdInt = parseInt(moveId, 10);
        // Check if the conversion is successful
        if (!isNaN(moveIdInt)) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'account.move',
                res_id: moveIdInt,
                views: [[false, "form"]],
                target: 'current',
            });
        }
    }
    updateResIdList() {
        // Get all resId values from the current rows and update the resIdList array
        const rows = this.__owl__.bdom.parentEl.ownerDocument.querySelectorAll('tr[data-resId]');
        this.resIdList = Array.from(rows).map(row => parseInt(row.getAttribute('data-resId'), 10));
    }

}
AccountMoveLineListController.template = 'base_accounting_kit.AccountMoveLineListController';
export const AccountMoveListView = {
    ...listView,
    Controller: AccountMoveLineListController,
};
registry.category('views').add('account_move_line_list_controller', AccountMoveListView);