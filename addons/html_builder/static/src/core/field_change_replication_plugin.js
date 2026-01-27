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
        this.fieldsToReplicate = new Set();
    }

    /**
     * @param { import("@html_editor/core/dom_observer_plugin").SerializedMutation[] } mutations
     */
    handleMutations(mutations) {
        mutations
            .filter(
                (m) =>
                    !(
                        m.type === EDITOR_MUTATION_TYPES.ATTRIBUTES &&
                        m.attributeName.startsWith("data-oe-t")
                    )
            )
            .map((m) => {
                let nodeId = m.nodeId;
                // TODO: Wouldn't doing this only for "remove" be enough?
                if (
                    [EDITOR_MUTATION_TYPES.ADD, EDITOR_MUTATION_TYPES.REMOVE].includes(m.type) &&
                    m.parentNodeId
                ) {
                    nodeId = m.parentNodeId;
                }
                return closestElement(
                    this.dependencies.domReferenceMap.getNodeById(nodeId),
                    "[data-oe-model], [data-oe-translation-source-sha]"
                );
            })
            .filter(Boolean)
            .forEach((fieldEl) => this.fieldsToReplicate.add(fieldEl));
    }

    onNormalizedPendingMutations() {
        const fields = this.fieldsToReplicate;
        this.fieldsToReplicate = new Set();
        const touchedEls = new Set();
        for (const sourceEl of fields) {
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
                    if (targetEl.innerHTML !== cloneEl.innerHTML) {
                        targetEl.replaceChildren(...cloneEl.cloneNode(true).childNodes);
                        touchedEls.add(targetEl);
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
