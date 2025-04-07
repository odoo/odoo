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
            EI =  mixins.pop()(EI);
        }
        if (!EI.name) {
            // if we get here, this is most likely because we have an anonymous
            // class. To make it easier to work with, we can add the name property
            // by doing a little hack
            const name = makeEditable.Interaction.name + "__mixin";
            EI = {[name]: class extends EI {}} [name];
        }
        result.push(EI);
    }
    return result;
}


registry.category("services").add("website_edit", {
    dependencies: ["public.interactions"],
    start(env, { ["public.interactions"]: publicInteractions }) {
        let editableInteractions = null;
        let previewInteractions = null;

        return {
            isEditingTranslations() {
                return !!publicInteractions.el.closest("html").dataset.edit_translations;
            },
            update(target, mode) {
                // editMode = true;
                // const currentEditMode = this.website_edit.mode === "edit";
                // interactions are already started. we only restart them if the
                // public root is not just starting.

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
            },
            stopInteractions(target) {
                publicInteractions.stopInteractions(target);
            },
        };
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
        const mode = options?.editableMode ? "edit" : false;
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
        fn = fn.bind(this.interaction);
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
