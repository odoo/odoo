import { Component, signal, t, useProps } from "@odoo/owl";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { FormSignalField } from "./form_signal_field";

/**
 * @typedef {import("./form_signal_arch_parser").ArchNode} ArchNode
 * @typedef {import("./form_signal_arch_parser").FieldNode} FieldNode
 * @typedef {import("./form_signal_arch_parser").NotebookNode} NotebookNode
 */

/**
 * Renders the arch tree built by the arch parser, with one recursive template
 * (`web.FormSignalRenderer.Node`). Fields are rendered by `FormSignalField`.
 *
 * The renderer never reads field values itself, except through modifiers
 * (`invisible`, `readonly`): it renders again when a field used in a modifier
 * changes, and leaves the other changes to the field components.
 */
export class FormSignalRenderer extends Component {
    static template = "web.FormSignalRenderer";
    static components = { FormSignalField };

    props = useProps({
        record: t.object(),
        archInfo: t.object(),
        /** field descriptions, from `fields_get` */
        fields: t.object(),
        /** values for the modifiers, see `NewRelationalModel.makeEvalContext` */
        evalContext: t.object(),
        readonly: t.boolean().optional(false),
    });

    /** @type {WeakMap<NotebookNode, ReturnType<typeof signal<number>>>} index of the active page */
    activePages = new WeakMap();

    /**
     * @param {{ invisible: string | null }} node
     */
    isVisible(node) {
        return !evaluateBooleanExpr(node.invisible, this.props.evalContext);
    }

    /**
     * @param {FieldNode} node
     */
    isReadonly(node) {
        if (this.props.readonly) {
            return true;
        }
        // the `readonly` attribute of the arch wins over the field definition
        return node.readonly !== null
            ? evaluateBooleanExpr(node.readonly, this.props.evalContext)
            : Boolean(this.props.fields[node.name].readonly);
    }

    /**
     * @param {{ string: string | null }} node a field or label node
     * @param {string | null} fieldName
     */
    getLabel(node, fieldName) {
        return node.string || this.props.fields[fieldName]?.string || "";
    }

    /**
     * A group of groups is laid out in columns, a group of fields as a grid of
     * labels and values.
     *
     * @param {import("./form_signal_arch_parser").GroupNode} node
     */
    isOuterGroup(node) {
        return node.children.some((child) => child.type === "group");
    }

    /**
     * In a group, an element right after a `<label>` goes in the value column.
     *
     * @param {ArchNode[]} children
     * @param {number} index
     */
    isAfterLabel(children, index) {
        return index > 0 && children[index - 1].type === "label";
    }

    /**
     * @param {NotebookNode} node
     */
    getActivePage(node) {
        const active = node.pages[this.getActivePageIndex(node)()];
        return active && this.isVisible(active)
            ? active
            : node.pages.find((p) => this.isVisible(p));
    }

    /**
     * @param {NotebookNode} node
     * @param {NotebookNode["pages"][number]} page
     */
    selectPage(node, page) {
        this.getActivePageIndex(node).set(node.pages.indexOf(page));
    }

    /**
     * @param {NotebookNode} node
     */
    getActivePageIndex(node) {
        if (!this.activePages.has(node)) {
            this.activePages.set(node, signal(0));
        }
        return this.activePages.get(node);
    }
}
