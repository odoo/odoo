import { Plugin } from "@html_editor/plugin";
import { memoize } from "@web/core/utils/functions";

/**
 * This plugin is responsible with providing the API to manipulate/insert
 * sub components in an editor.
 */
export class EmbeddedComponentPlugin extends Plugin {
    static name = "embedded_components";
    static dependencies = ["history", "protected_node"];
    resources = {
        filter_descendants_to_serialize: this.filterDescendantsToSerialize.bind(this),
        is_mutation_record_savable: this.isMutationRecordSavable.bind(this),
        on_change_attribute: this.onChangeAttribute.bind(this),
        onExternalHistorySteps: this.handleComponents.bind(this, this.editable),
    };

    setup() {
        this.components = new Set();
        // map from node to component info
        this.nodeMap = new WeakMap();
        this.app = this.config.embeddedComponentInfo.app;
        this.env = this.config.embeddedComponentInfo.env;
        this.hostToStateChangeManagerMap = new WeakMap();
        this.embeddedComponents = memoize((embeddedComponents = []) => {
            const result = {};
            for (const embedding of embeddedComponents) {
                // TODO ABD: Any embedding with the same name as another will overwrite it.
                // File currently relies on this system. Change it ?
                result[embedding.name] = embedding;
            }
            return result;
        });
        // First mount is done during HISTORY_RESET which happens during START_EDITION
    }

    isMutationRecordSavable(record) {
        const info = this.nodeMap.get(record.target);
        if (
            info &&
            record.type === "attributes" &&
            record.attributeName === "data-embedded-props"
        ) {
            // This attribute is determined independently for each user
            // through `data-embedded-state` attribute mutations.
            return false;
        }
        return true;
    }

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE": {
                this.normalize(payload.node);
                break;
            }
            case "CLEAN_FOR_SAVE": {
                this.cleanForSave(payload.root);
                break;
            }
            case "RESTORE_SAVEPOINT":
            case "HISTORY_RESET_FROM_STEPS":
            case "HISTORY_RESET": {
                this.handleComponents(this.editable);
                break;
            }
            case "STEP_ADDED": {
                this.handleComponents(payload.stepCommonAncestor);
                break;
            }
        }
    }

    filterDescendantsToSerialize(elem) {
        const embedding = this.getEmbedding(elem);
        if (!embedding) {
            return;
        }
        return Object.values(embedding.getEditableDescendants?.(elem) || {});
    }

    handleComponents(elem) {
        this.destroyRemovedComponents([...this.components]);
        this.forEachEmbeddedComponentHost(elem, (host, embedding) => {
            const info = this.nodeMap.get(host);
            if (!info) {
                this.mountComponent(host, embedding);
            }
        });
    }

    forEachEmbeddedComponentHost(elem, callback) {
        const selector = `[data-embedded]`;
        const targets = [...elem.querySelectorAll(selector)];
        if (elem.matches(selector)) {
            targets.unshift(elem);
        }
        for (const host of targets) {
            const embedding = this.getEmbedding(host);
            if (!embedding) {
                continue;
            }
            callback(host, embedding);
        }
    }

    getEmbedding(host) {
        return this.embeddedComponents(this.getResource("embeddedComponents"))[
            host.dataset.embedded
        ];
    }

    /**
     * Apply an embedded state change received from `data-embedded-state`
     * attribute. In some cases (undo/redo/revertStepsUntil history operations),
     * the attribute has to be set to a new value, computed by the
     * stateChangeManager.
     *
     * @param {Object} attributeChange @see HistoryPlugin
     * @param { Object } options
     * @param { boolean } options.forNewStep whether the mutation is being used
     *        to create a new step
     * @returns {string|undefined} new attribute value to set on the node if
     *          attributeChange.value has to be altered, undefined if
     *          attributeChange.value is already correct.
     */
    onChangeAttribute(attributeChange, { forNewStep = false } = {}) {
        if (attributeChange.attributeName !== "data-embedded-state") {
            return;
        }
        const attrState = attributeChange.reverse
            ? attributeChange.oldValue
            : attributeChange.value;
        const stateChangeManager = this.getStateChangeManager(attributeChange.target);
        if (stateChangeManager) {
            return stateChangeManager.onStateChanged(attrState, {
                reverse: attributeChange.reverse,
                forNewStep,
            });
        }
    }

    getStateChangeManager(host) {
        const embedding = this.getEmbedding(host);
        if (!("getStateChangeManager" in embedding)) {
            return null;
        }
        if (!this.hostToStateChangeManagerMap.has(host)) {
            const config = {
                host,
                dispatch: this.dispatch.bind(this),
            };
            const stateChangeManager = embedding.getStateChangeManager(config);
            stateChangeManager.setup();
            this.hostToStateChangeManagerMap.set(host, stateChangeManager);
        }
        return this.hostToStateChangeManagerMap.get(host);
    }

    mountComponent(
        host,
        { Component, getEditableDescendants, getProps, name, getStateChangeManager }
    ) {
        const props = getProps?.(host) || {};
        const env = Object.create(this.env);
        if (getStateChangeManager) {
            env.getStateChangeManager = this.getStateChangeManager.bind(this);
        }
        if (getEditableDescendants) {
            env.getEditableDescendants = getEditableDescendants;
        }
        this.dispatch("SETUP_NEW_COMPONENT", {
            name,
            env,
            props,
        });
        const root = this.app.createRoot(Component, {
            props,
            env,
        });
        root.mount(host);
        // Patch mount fiber to hook into the exact call stack where root is
        // mounted (but before). This will remove host children synchronously
        // just before adding the root rendered html.
        const fiber = root.node.fiber;
        const fiberComplete = fiber.complete;
        fiber.complete = function () {
            host.replaceChildren();
            fiberComplete.call(this);
        };
        const info = {
            root,
            host,
        };
        this.components.add(info);
        this.nodeMap.set(host, info);
    }

    destroyRemovedComponents(infos) {
        for (const info of infos) {
            if (!this.editable.contains(info.host)) {
                const host = info.host;
                const display = host.style.display;
                const parentNode = host.parentNode;
                const clone = host.cloneNode(false);
                if (parentNode) {
                    parentNode.replaceChild(clone, host);
                }
                host.style.display = "none";
                this.editable.after(host);
                this.destroyComponent(info);
                if (parentNode) {
                    parentNode.replaceChild(host, clone);
                } else {
                    host.remove();
                }
                host.style.display = display;
                if (!host.getAttribute("style")) {
                    host.removeAttribute("style");
                }
            }
        }
    }

    deepDestroyComponent({ host }) {
        const removed = [];
        this.forEachEmbeddedComponentHost(host, (containedHost) => {
            const info = this.nodeMap.get(containedHost);
            if (info) {
                if (this.editable.contains(containedHost)) {
                    this.destroyComponent(info);
                } else {
                    removed.push(info);
                }
            }
        });
        this.destroyRemovedComponents(removed);
    }

    /**
     * Should not be called directly as it will not handle recursivity and
     * removed components @see deepDestroyComponent
     */
    destroyComponent({ root, host }) {
        const { getEditableDescendants } = this.getEmbedding(host);
        const editableDescendants = getEditableDescendants?.(host) || {};
        root.destroy();
        this.components.delete(arguments[0]);
        this.nodeMap.delete(host);
        host.append(...Object.values(editableDescendants));
    }

    destroy() {
        super.destroy();
        for (const info of [...this.components]) {
            if (this.components.has(info)) {
                this.deepDestroyComponent(info);
            }
        }
    }

    normalize(elem) {
        this.forEachEmbeddedComponentHost(elem, (host, { getEditableDescendants }) => {
            this.shared.setProtectingNode(host, true);
            const editableDescendants = getEditableDescendants?.(host) || {};
            for (const editableDescendant of Object.values(editableDescendants)) {
                this.shared.setProtectingNode(editableDescendant, false);
            }
        });
    }

    cleanForSave(clone) {
        this.forEachEmbeddedComponentHost(clone, (host, { getEditableDescendants }) => {
            // In this case, host is a cloned element, there is no OWL root
            // attached to it.
            const editableDescendants = getEditableDescendants?.(host) || {};
            host.replaceChildren();
            for (const editableDescendant of Object.values(editableDescendants)) {
                delete editableDescendant.dataset.oeProtected;
                host.append(editableDescendant);
            }
            delete host.dataset.oeProtected;
            delete host.dataset.embeddedState;
        });
    }
}
