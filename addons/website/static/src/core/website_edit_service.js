import { registry } from "@web/core/registry";

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
        let editMode = false;

        return {
            isEditingTranslations() {
                return !!publicInteractions.el.closest("html").dataset.edit_translations;
            },
            update(target, mode) {
                // editMode = true;
                // const currentEditMode = this.website_edit.mode === "edit";
                const shouldActivateEditInteractions = editMode !== mode;
                // interactions are already started. we only restart them if the
                // public root is not just starting.

                publicInteractions.stopInteractions(target);
                if (shouldActivateEditInteractions) {
                    if (!editableInteractions) {
                        const builders = registry.category("website.editable_active_elements_builders").getAll();
                        editableInteractions = buildEditableInteractions(builders);
                    }
                    editMode = true;
                    publicInteractions.activate(editableInteractions);
                } else {
                    publicInteractions.startInteractions(target);
                }

            }
        };
    },
});
