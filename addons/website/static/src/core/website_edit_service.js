import { registry } from "@web/core/registry";
import { PublicRoot } from "@web/legacy/js/public/public_root";
import { Colibri } from "@web/public/colibri";
import { Interaction } from "@web/public/interaction";
import { patch } from "@web/core/utils/patch";
import { setupIgnoreDOMMutations } from "@website/js/content/auto_hide_menu";
import { omit } from "@web/core/utils/objects";

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

export const websiteEditService = {
    dependencies: ["public.interactions"],
    start(env, { ["public.interactions"]: publicInteractions }) {
        let editableInteractions = null;
        let previewInteractions = null;
        const patches = [];
        const historyCallbacks = {};
        const shared = {};

        const update = (target, mode) => {
            // editMode = true;
            // const currentEditMode = this.website_edit.mode === "edit";

            // interactions are already started. we only restart them if the
            // public root is not just starting.
            stopDisconnectedInteractions();
            publicInteractions.stopInteractions(target);
            if (mode === "edit") {
                if (!editableInteractions) {
                    const builders = registry.category("public.interactions.edit").getAll();
                    editableInteractions = buildEditableInteractions(builders);
                }
                publicInteractions.editMode = true;
                publicInteractions.activate(editableInteractions);
            } else if (mode === "preview") {
                if (!previewInteractions) {
                    const builders = registry.category("public.interactions.preview").getAll();
                    previewInteractions = buildEditableInteractions(builders);
                }
                publicInteractions.activate(previewInteractions, target);
            } else {
                publicInteractions.startInteractions(target);
            }
        };

        const refresh = (target) => {
            publicInteractions.isRefreshing = true;
            try {
                update(target, "edit");
            } finally {
                publicInteractions.isRefreshing = false;
            }
        };

        const stop = (target) => {
            publicInteractions.stopInteractions(target);
        };

        const stopInteraction = (name) => {
            publicInteractions.stopInteractionByName(name);
        };

        const stopDisconnectedInteractions = () => {
            for (const interaction of publicInteractions.interactions) {
                if (!interaction.el.isConnected) {
                    stop(interaction.el);
                }
            }
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
                        this.interaction.setupConfigurationSnapshot();
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
                        const boundFn = fn.bind(this.interaction);
                        if (event.startsWith("slide.bs.carousel")) {
                            // Never allow cancelling this event in edit mode.
                            fn = (...args) => {
                                const ev = args[0];
                                ev.preventDefault = () => {};
                                ev.stopPropagation = () => {};
                                return boundFn(...args);
                            };
                        } else {
                            fn = boundFn;
                        }
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
                    startInteraction(...args) {
                        historyCallbacks.ignoreDOMMutations(() => super.startInteraction(...args));
                    },
                }),
                patch(Interaction.prototype, {
                    setupConfigurationSnapshot() {
                        // Track configuration values.
                        this.configurationSnapshot = this.getConfigurationSnapshot();
                    },
                    getConfigurationSnapshot() {
                        // Naive generalise implementation of a snapshot that
                        // would impact the behavior of an interaction.
                        // To be overloaded by edit-mode interactions that need
                        // something more specific.
                        // TODO Sort keys to improve comparison.
                        const dataset = omit(this.el.dataset, "visibility");
                        const style = {};
                        for (const property of this.el.style) {
                            if (property.startsWith("animation")) {
                                if (property === "animation-play-state") {
                                    continue;
                                }
                                style[property] = this.el.style[property];
                            }
                        }
                        if (Object.keys(dataset).length || style.length) {
                            return JSON.stringify({ dataset, style });
                        }
                        return NaN; // So that it is different from itself
                    },
                    shouldStop() {
                        if (!this.el.isConnected) {
                            return true;
                        }
                        // Selector does not match anymore ?
                        const I = this.constructor;
                        let isMatch = this.el.matches(I.selector);
                        if (I.selectorHas) {
                            isMatch &&= !!this.el.querySelector(I.selectorHas);
                        }
                        if (I.selectorNotHas) {
                            isMatch &&= !this.el.querySelector(I.selectorNotHas);
                        }
                        if (!isMatch) {
                            return true;
                        }
                        // Configuration changed ?
                        const snapshot = this.getConfigurationSnapshot();
                        if (snapshot === this.configurationSnapshot) {
                            return false;
                        }
                        this.configurationSnapshot = snapshot;
                        return true;
                    },
                    isImpactedBy(el) {
                        return false;
                    },
                    insert(...args) {
                        const el = args[0];
                        super.insert(...args);
                        el.setAttribute("contenteditable", "false");
                    },
                }),
                patch(publicInteractions.constructor.prototype, {
                    shouldStop(el, interaction) {
                        if (this.isRefreshing) {
                            const mustBeRefreshed =
                                super.shouldStop(el, interaction) ||
                                interaction.interaction.isImpactedBy(el);
                            return mustBeRefreshed && interaction.interaction.shouldStop();
                        }
                        return super.shouldStop(el, interaction);
                    },

                    stopInteractionByName(name) {
                        const IToStop = registry.category("public.interactions").get(name);
                        const interactions = [];
                        for (const interaction of this.interactions) {
                            if (interaction.interaction.constructor === IToStop) {
                                interaction.destroy();
                                this.activeInteractions.delete(interaction.el, IToStop);
                            } else {
                                interactions.push(interaction);
                            }
                        }
                        this.interactions = interactions;
                    },
                })
            );
        };
        const uninstallPatches = () => {
            for (const removePatch of patches) {
                removePatch();
            }
            patches.length = 0;
            setupIgnoreDOMMutations(null);
        };
        const applyAction = (actionId, spec) => {
            shared.builderActions.applyAction(actionId, spec);
        };
        const callShared = (pluginName, methodName, args = []) => {
            if (!Array.isArray(args)) {
                args = [args];
            }
            if (shared[pluginName]) {
                if (shared[pluginName][methodName]) {
                    return shared[pluginName][methodName](...args);
                } else {
                    console.error(`Method "${methodName}" not found on plugin "${pluginName}".`);
                }
            } else {
                console.error(`Plugin "${pluginName}" not found.`);
            }
        };

        const websiteEditService = {
            isEditingTranslations,
            update,
            refresh,
            stop,
            stopInteraction,
            installPatches,
            uninstallPatches,
            applyAction,
            callShared,
        };

        const handleEditPage = (ev) => {
            stop(ev.detail.iframeDocument);
        };

        // Transfer the iframe website_edit service to the EditInteractionPlugin
        const handlePluginLoaded = (ev) => {
            ev.currentTarget.dispatchEvent(
                new CustomEvent("transfer_website_edit_service", {
                    detail: {
                        websiteEditService,
                    },
                })
            );
            Object.assign(shared, ev.shared);
            historyCallbacks.ignoreDOMMutations = shared.history.ignoreDOMMutations;
            setupIgnoreDOMMutations(shared.history.ignoreDOMMutations);
        };

        window.parent.document.addEventListener("edit_page", handleEditPage);
        window.parent.document.addEventListener(
            "edit_interaction_plugin_loaded",
            handlePluginLoaded
        );

        // Clean up parent document listeners when iframe unloads to prevent
        // stale handlers from serving an outdated service to new plugins.
        window.addEventListener("beforeunload", () => {
            window.parent.document.removeEventListener("edit_page", handleEditPage);
            window.parent.document.removeEventListener(
                "edit_interaction_plugin_loaded",
                handlePluginLoaded
            );
        });

        return websiteEditService;
    },
};
registry.category("services").add("website_edit", websiteEditService);

// Patch PublicRoot.

PublicRoot.include({
    // This file is lazy loaded, init will not be called when entering edit.
    /**
     * @override
     */
    _restartInteractions(targetEl, options) {
        const websiteEdit = this.bindService("website_edit");
        const mode = options?.editableMode ? "edit" : "normal";
        websiteEdit.update(targetEl, mode);
    },
});

// Patch Colibri.

patch(Colibri.prototype, {
    protectSyncAfterAsync(interaction, name, fn) {
        fn = super.protectSyncAfterAsync(interaction, name, fn);
        const fullName = `${interaction.constructor.name}/${name}`;
        return (...args) => {
            // TODO No jQuery ?
            const wysiwyg = window.$?.("#wrapwrap").data("wysiwyg");
            wysiwyg?.odooEditor.observerUnactive(fullName);
            const result = fn(...args);
            wysiwyg?.odooEditor.observerActive(fullName);
            return result;
        };
    },
    addListener(target, event, fn, options) {
        const boundFn = fn.bind(this.interaction);
        if (event.startsWith("slide.bs.carousel")) {
            // Never allow cancelling this event in edit mode.
            fn = (...args) => {
                const ev = args[0];
                ev.preventDefault = () => {};
                ev.stopPropagation = () => {};
                return boundFn(...args);
            };
        } else {
            fn = boundFn;
        }
        let stealth = true;
        const parts = event.split(".");
        if (parts.includes("keepInHistory") || options?.keepInHistory) {
            stealth = false;
            event = parts.filter((part) => part !== "keepInHistory").join(".");
            delete options?.keepInHistory;
        }
        // TODO No jQuery ?
        const wysiwyg = window.$?.("#wrapwrap").data("wysiwyg");
        let stealthFn = fn;
        if (wysiwyg?.odooEditor && !fn.isHandler && stealth) {
            const name = `${this.interaction.constructor.name}/${event}`;
            stealthFn = (...args) => {
                wysiwyg.odooEditor.observerUnactive(name);
                const result = fn(...args);
                wysiwyg.odooEditor.observerActive(name);
                return result;
            };
        }
        return super.addListener(target, event, stealthFn, options);
    },
    applyAttr(el, attr, value) {
        // TODO No jQuery ?
        const wysiwyg = window.$?.("#wrapwrap").data("wysiwyg");
        const name = `${this.interaction.constructor.name}/${attr}`;
        wysiwyg?.odooEditor.observerUnactive(name);
        super.applyAttr(...arguments);
        wysiwyg?.odooEditor.observerActive(name);
    },
    applyTOut(el, value) {
        // TODO No jQuery ?
        const wysiwyg = window.$?.("#wrapwrap").data("wysiwyg");
        const name = `${this.interaction.constructor.name}/t-out`;
        wysiwyg?.odooEditor.observerUnactive(name);
        super.applyTOut(...arguments);
        wysiwyg?.odooEditor.observerActive(name);
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
