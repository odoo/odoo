import { registry } from "@web/core/registry";
import { PublicRoot } from "@web/legacy/js/public/public_root";
import { Colibri } from "@web/public/colibri";
import { patch } from "@web/core/utils/patch";

export function buildEditableInteractions(builders) {
    const result = [];

    const mixinPerInteraction = new Map();
    for (const makeEditable of builders) {
        mixinPerInteraction.set(makeEditable.Interaction, makeEditable.mixin || ((C) => C));
    }
    for (const makeEditable of builders) {
        if (makeEditable.isAbstract) {
            continue;
        }
        let I = makeEditable.Interaction;
        // Collect mixins to up to Interaction class in reverse order.
        const mixins = [];
        while (I.name !== "Interaction") {
            const mixin = mixinPerInteraction.get(I);
            if (mixin) {
                mixins.push(mixin);
            } else {
                console.log(`No mixin defined for: ${I.name}`);
            }
            I = I.__proto__;
        }
        // Apply mixins from top-most class.
        let EI = makeEditable.Interaction;
        while (mixins.length) {
            EI = mixins.pop()(EI);
        }
        if (!EI.name) {
            // if we get here, this is most likely because we have an anonymous
            // class. To make it easier to work with, we can add the name property
            // by doing a little hack
            const name = makeEditable.Interaction.name + "__mixin";
            EI = { [name]: class extends EI {} }[name];
        }
        result.push(EI);
    }
    return result;
}

registry.category("services").add("website_edit", {
    dependencies: ["public.interactions"],
    start(env, { ["public.interactions"]: publicInteractions }) {
        let editableInteractions = null;
        let editMode = false;
        const patches = [];
        const historyCallbacks = {};

        const update = (target, mode) => {
            // editMode = true;
            // const currentEditMode = this.website_edit.mode === "edit";
            const shouldActivateEditInteractions = editMode !== mode;
            // interactions are already started. we only restart them if the
            // public root is not just starting.

            publicInteractions.stopInteractions(target);
            if (shouldActivateEditInteractions) {
                if (!editableInteractions) {
                    const builders = registry.category("public.interactions.edit").getAll();
                    editableInteractions = buildEditableInteractions(builders);
                }
                editMode = true;
                publicInteractions.editMode = true;
                publicInteractions.activate(editableInteractions);
            } else {
                publicInteractions.startInteractions(target);
            }
        };

        const stop = (target) => {
            publicInteractions.stopInteractions(target);
        };

        const isEditingTranslations = () =>
            !!publicInteractions.el.closest("html").dataset.edit_translations;

        const installPatches = () => {
            if (patches.length) {
                return;
            }

            // Patch Colibri.

            patches.push(
                patch(Colibri.prototype, {
                    setupInteraction() {
                        historyCallbacks.ignoreDOMMutations(() => {
                            super.setupInteraction();
                        });
                    },
                    destroyInteraction() {
                        historyCallbacks.ignoreDOMMutations(() => {
                            super.destroyInteraction();
                        });
                    },
                    protectSyncAfterAsync(interaction, name, fn) {
                        fn = super.protectSyncAfterAsync(interaction, name, fn);
                        return (...args) => historyCallbacks.ignoreDOMMutations(() => fn(...args));
                    },
                    addListener(target, event, fn, options) {
                        fn = fn.bind(this.interaction);
                        let stealth = true;
                        const parts = event.split(".");
                        if (parts.includes("keepInHistory") || options?.keepInHistory) {
                            stealth = false;
                            event = parts.filter((part) => part !== "keepInHistory").join(".");
                            delete options?.keepInHistory;
                        }
                        let stealthFn = fn;
                        if (historyCallbacks.ignoreDOMMutations && !fn.isHandler && stealth) {
                            stealthFn = (...args) =>
                                historyCallbacks.ignoreDOMMutations(() => fn(...args));
                        }
                        return super.addListener(target, event, stealthFn, options);
                    },
                    applyAttr(...args) {
                        historyCallbacks.ignoreDOMMutations(() => super.applyAttr(...args));
                    },
                    applyTOut(...args) {
                        historyCallbacks.ignoreDOMMutations(() => super.applyTOut(...args));
                    },
                })
            );
        };
        const uninstallPatches = () => {
            for (const removePatch of patches) {
                removePatch();
            }
            patches.length = 0;
        };

        const websiteEditService = {
            isEditingTranslations,
            update,
            stop,
            installPatches,
            uninstallPatches,
        };

        // Transfer the iframe website_edit service to the EditInteractionPlugin
        window.parent.document.addEventListener("edit_interaction_plugin_loaded", (ev) => {
            ev.currentTarget.dispatchEvent(
                new CustomEvent("transfer_website_edit_service", {
                    detail: {
                        websiteEditService,
                    },
                })
            );
            Object.assign(historyCallbacks, ev.historyCallbacks);
        });

        return websiteEditService;
    },
});

// Patch PublicRoot.

PublicRoot.include({
    // This file is lazy loaded, init will not be called when entering edit.
    /**
     * @override
     */
    _restartInteractions(targetEl, options) {
        const websiteEdit = this.bindService("website_edit");
        websiteEdit.update(targetEl, options?.editableMode || false);
    },
});

export function withHistory(dynamicContent) {
    const result = {};
    for (const [selector, content] of Object.entries(dynamicContent)) {
        result[selector] = {};
        for (const [key, value] of Object.entries(content)) {
            result[selector][key.startsWith("t-on-") ? `${key}.keepInHistory` : key] = value;
        }
    }
    return result;
}
