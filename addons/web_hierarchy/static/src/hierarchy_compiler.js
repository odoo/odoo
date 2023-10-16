/** @odoo-module **/

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";

export class HierarchyCompiler extends KanbanCompiler {
    /**
     * @override
     * @param {Element} el
     * @param {Object} params
     * @returns {Element}
     */
    compileField(el, params) {
        const fieldName = el.getAttribute("name");
        return super.compileField(el, {
            ...(params || {}),
            recordExpr: "__record__",
            dataPointId: "__comp__.props.node.id",
            formattedValueExpr: `record['${fieldName}'].value`,
        });
    }

    compileButton(el, params) {
        return super.compileButton(el, {
            ...(params || {}),
            recordExpr: "__record__",
        });
    }
}
