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
            dataPointIdExpr: "__comp__.props.node.id",
            formattedValueExpr: `record['${fieldName}'].value`,
        });
    }

    compileButton(el, params) {
        return super.compileButton(el, {
            ...(params || {}),
            recordExpr: "__record__",
        });
    }

    /**
     * Allow access to the record during compilation, to properly evaluate
     * invisible on any hierarchy card nodes declared in the view.
     *
     * @override
     */
    compileNode(node, params = {}, evalInvisible = true) {
        return super.compileNode(
            node,
            {
                ...params,
                recordExpr: "__record__",
            },
            evalInvisible
        );
    }
}
