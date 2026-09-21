import { EDITOR_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * @typedef {((arg: { sourceEl: HTMLElement, targetEl: HTMLElement }) => void)[]} on_replicated_handlers
 */

export class FieldChangeReplicationPlugin extends Plugin {
    static id = "fieldChangeReplication";
    static dependencies = ["dom", "domReferenceMap"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        on_pending_mutations_staged_handlers: this.handleMutations.bind(this),
        on_pending_mutations_normalized_handlers: this.onNormalizedPendingMutations.bind(this),
    };

    setup() {
        this.mutationsBySource = new Map();
    }

    /**
     * @param { import("@html_editor/core/dom_observer_plugin").SerializedMutation[] } mutations
     */
    handleMutations(mutations) {
        for (const mutation of mutations) {
            if (
                mutation.type === EDITOR_MUTATION_TYPES.ATTRIBUTES &&
                mutation.attributeName.startsWith("data-oe-t")
            ) {
                continue;
            }
            let nodeId = mutation.nodeId;
            // TODO: Wouldn't doing this only for "remove" be enough?
            if (
                [EDITOR_MUTATION_TYPES.ADD, EDITOR_MUTATION_TYPES.REMOVE].includes(mutation.type) &&
                mutation.parentNodeId
            ) {
                nodeId = mutation.parentNodeId;
            }
            const fieldEl = closestElement(
                this.dependencies.domReferenceMap.getNodeById(nodeId),
                "[data-oe-model], [data-oe-translation-source-sha]"
            );
            // Do not forward "unstyled" copies to other nodes.
            if (!fieldEl || fieldEl.classList.contains("o_translation_without_style")) {
                continue;
            }
            if (!this.mutationsBySource.has(fieldEl)) {
                this.mutationsBySource.set(fieldEl, []);
            }
            this.mutationsBySource.get(fieldEl).push(mutation);
        }
    }

    onNormalizedPendingMutations() {
        const mutationsBySource = this.mutationsBySource;
        this.mutationsBySource = new Map();
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
                this.processThrough("clean_for_save_processors", cloneEl);
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
                            if (
                                this.dependencies.domReferenceMap.getNodeById(mutation.nodeId) !==
                                sourceEl
                            ) {
                                continue;
                            }
                            if (mutation.type === EDITOR_MUTATION_TYPES.CLASS_LIST) {
                                targetEl.classList.toggle(mutation.className, mutation.value);
                            } else if (
                                mutation.type === EDITOR_MUTATION_TYPES.ATTRIBUTES &&
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
                    this.trigger("on_replicated_handlers", { sourceEl, targetEl });
                }
            }
        }
        for (const touchedEl of touchedEls) {
            this.processThrough("normalize_processors", touchedEl);
        }
    }
}
