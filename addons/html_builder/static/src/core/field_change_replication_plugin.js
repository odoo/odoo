import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

/**
 * @typedef {((arg: { sourceEl: HTMLElement, targetEl: HTMLElement }) => void)[]} after_replication_handlers
 */

export class FieldChangeReplicationPlugin extends Plugin {
    static id = "fieldChangeReplication";
    static dependencies = ["dom"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        handleNewRecords: this.handleMutations.bind(this),
        normalize_handlers: withSequence(9000, this.normalizeHandler.bind(this)),
    };

    setup() {
        this.mutationsBySource = new Map();
    }

    /**
     * @param { import("@html_editor/core/history_plugin").HistoryMutationRecord[] } records
     */
    handleMutations(records) {
        for (const record of records) {
            if (record.type === "attributes" && record.attributeName.startsWith("data-oe-t")) {
                continue;
            }
            const fieldEl = closestElement(
                record.target,
                "[data-oe-model], [data-oe-translation-source-sha]"
            );
            // Do not forward "unstyled" copies to other nodes.
            if (!fieldEl || fieldEl.classList.contains("o_translation_without_style")) {
                continue;
            }
            if (!this.mutationsBySource.has(fieldEl)) {
                this.mutationsBySource.set(fieldEl, []);
            }
            this.mutationsBySource.get(fieldEl).push(record);
        }
    }

    /**
     * @param { Node } commonAncestor
     * @param { "original"|"undo"|"redo"|"restore" } stepState
     */
    normalizeHandler(commonAncestor, stepState) {
        const mutationsBySource = this.mutationsBySource;
        this.mutationsBySource = new Map();
        if (stepState !== "original") {
            return;
        }
        const touchedEls = new Set();
        for (const sourceEl of mutationsBySource.keys()) {
            const same = (attribute, quote = '"') =>
                `[${attribute}=${quote}${sourceEl.getAttribute(attribute)}${quote}]`;
            let selector = "";
            if (sourceEl.getAttribute("data-oe-model")) {
                selector += same("data-oe-model") + same("data-oe-id") + same("data-oe-field");
            }
            if (sourceEl.getAttribute("data-oe-translation-source-sha")) {
                selector += same("data-oe-translation-source-sha");
            }
            if (sourceEl.getAttribute("data-oe-type")) {
                selector += same("data-oe-type");
            }
            if (sourceEl.getAttribute("data-oe-expression")) {
                selector += same("data-oe-expression");
            } else if (sourceEl.getAttribute("data-oe-xpath")) {
                selector += same("data-oe-xpath");
            }
            if (sourceEl.getAttribute("data-oe-contact-options")) {
                selector += same("data-oe-contact-options", "'");
            }

            if (sourceEl.getAttribute("data-oe-type") === "many2one") {
                selector +=
                    ",[data-oe-model]" +
                    same("data-oe-type") +
                    same("data-oe-many2one-model") +
                    same("data-oe-many2one-id");
                selector +=
                    ",[data-oe-model][data-oe-field=name]" +
                    `[data-oe-model="${sourceEl.getAttribute("data-oe-many2one-model")}"]` +
                    `[data-oe-id="${sourceEl.getAttribute("data-oe-many2one-id")}"]`;
            }

            if (sourceEl.getAttribute("data-oe-field") === "name") {
                selector +=
                    ",[data-oe-model][data-oe-type=many2one]" +
                    `[data-oe-many2one-model="${sourceEl.getAttribute("data-oe-model")}"]` +
                    `[data-oe-many2one-id="${sourceEl.getAttribute("data-oe-id")}"]`;
            }

            const targetEls = [...this.editable.querySelectorAll(selector)].filter(
                (targetEl) => targetEl !== sourceEl
            );
            if (targetEls.length) {
                const cloneEl = sourceEl.cloneNode(true);
                cloneEl.toggleAttribute("contenteditable", sourceEl.isContentEditable);
                this.dependencies.dom.removeSystemProperties(cloneEl);
                this.dispatchTo("clean_for_save_handlers", { root: cloneEl });
                for (const targetEl of targetEls) {
                    if (targetEl.classList.contains("o_translation_without_style")) {
                        // For generated elements such as the navigation
                        // labels of website's table of content, only the
                        // text of the referenced translation must be used.
                        if (targetEl.innerText !== cloneEl.innerText) {
                            targetEl.innerText = cloneEl.innerText;
                            touchedEls.add(targetEl);
                        }
                    } else {
                        if (targetEl.innerHTML !== cloneEl.innerHTML) {
                            targetEl.replaceChildren(...cloneEl.cloneNode(true).childNodes);
                            touchedEls.add(targetEl);
                        }
                    }
                    if (
                        targetEl.getAttribute("data-oe-model") === "ir.ui.view" &&
                        targetEl.getAttribute("data-oe-field") === "arch"
                    ) {
                        for (const mutation of mutationsBySource.get(sourceEl)) {
                            if (mutation.target !== sourceEl) {
                                continue;
                            }
                            if (mutation.type === "classList") {
                                targetEl.classList.toggle(mutation.className, mutation.value);
                            } else if (
                                mutation.type === "attributes" &&
                                (this.config.allowedRootAttrs || []).includes(
                                    mutation.attributeName
                                )
                            ) {
                                if (mutation.value === null) {
                                    targetEl.removeAttribute(mutation.attributeName);
                                } else {
                                    targetEl.setAttribute(mutation.attributeName, mutation.value);
                                }
                            }
                        }
                    }
                    this.dispatchTo("after_replication_handlers", { sourceEl, targetEl });
                }
            }
        }
        for (const touchedEl of touchedEls) {
            this.dispatchTo("normalize_handlers", touchedEl);
        }
    }
}
