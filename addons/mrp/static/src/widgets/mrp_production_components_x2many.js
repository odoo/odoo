/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onPatched } from "@odoo/owl";

export class MrpProductionComponentsListRenderer extends ListRenderer {
    setup() {
        super.setup();
        let hasNewLineListener = false;
        let isNewLineClicked = false;
        let currentStatusBar = null;

        const updateStatusBar = () => {
            const newStatusBar = document.querySelector('.state');
            if (isNewLineClicked && currentStatusBar !== newStatusBar) {
                this.keepColumnWidths = false;
                currentStatusBar = newStatusBar;
            }
        };

        const attachNewLineListener = () => {
            const addLineButton = document.querySelector('.o_field_x2many_list_row_add a');
            if (addLineButton && !hasNewLineListener) {
                addLineButton.addEventListener('click', () => {
                    isNewLineClicked = true;
                    currentStatusBar = document.querySelector('.o_statusbar_status');
                });
                hasNewLineListener = true;
            }
        };
    
        onPatched(() => {
            updateStatusBar();
            attachNewLineListener();
        });
    }

    getCellClass(column, record) {
        let classNames = super.getCellClass(...arguments);
        if (column.name == "quantity_done" && !record.data.manual_consumption) {
            classNames += ' o_non_manual_consumption';
        }
        return classNames;
    }
}

export class MrpProductionComponentsX2ManyField extends X2ManyField {}
MrpProductionComponentsX2ManyField.components = { ...X2ManyField.components, ListRenderer: MrpProductionComponentsListRenderer };

MrpProductionComponentsX2ManyField.additionalClasses = ['o_field_many2many'];
registry.category("fields").add("mrp_production_components_x2many", MrpProductionComponentsX2ManyField);
