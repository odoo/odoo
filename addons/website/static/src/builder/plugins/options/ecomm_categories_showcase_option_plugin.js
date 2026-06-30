import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { BuilderAction } from "@html_builder/core/builder_action";

export class EcommCategoriesShowcaseOptionPlugin extends Plugin {
    static id = "ecommCategoriesShowcaseOption";

    static DEFAULT_BLOCK_COUNT = 3;
    static MIN_BLOCK_COUNT = 2;
    static MAX_BLOCK_COUNT = 4;
    static GAP_CLASS = "gap-4";
    static DEFAULT_ROUNDNESS = "rounded-2";
    static NO_ROUNDNESS = "rounded-0";
    static ROUNDNESS_CLASSES = [
        "rounded-0",
        "rounded-1",
        "rounded-2",
        "rounded-3",
        "rounded-4",
        "rounded-5",
    ];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            BlockCountAction,
            SpacingToggleAction,
            AddEcommCategoriesShowcaseBlockAction,
        },
        clean_for_save_processors: this.cleanForSave.bind(this),
        dropzone_selectors: {
            selector: ".s_ecomm_categories_showcase_block",
            dropNear: ".s_ecomm_categories_showcase_block",
        },
    };

    cleanForSave(rootEl) {
        for (const snippetEl of rootEl.querySelectorAll(".s_ecomm_categories_showcase")) {
            const wrapperEl = snippetEl.querySelector(".s_ecomm_categories_showcase_wrapper");
            if (!wrapperEl || wrapperEl.children.length === 0) {
                snippetEl.remove();
            }
        }
    }

    static _updateBlocksRoundness(editingElement, roundnessClass) {
        const blocks = editingElement.querySelectorAll(".s_ecomm_categories_showcase_block");
        blocks.forEach((block) => {
            block.classList.remove(...EcommCategoriesShowcaseOptionPlugin.ROUNDNESS_CLASSES);
            block.classList.add(roundnessClass);
        });
    }
}

export class BlockCountAction extends BuilderAction {
    static id = "blockCount";

    getValue({ editingElement }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        if (!wrapper) {
            return EcommCategoriesShowcaseOptionPlugin.DEFAULT_BLOCK_COUNT.toString();
        }
        return wrapper.querySelectorAll(".s_ecomm_categories_showcase_block").length.toString();
    }

    apply({ editingElement, value }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        if (!wrapper) {
            return;
        }

        const count = parseInt(value, 10);
        if (
            isNaN(count) ||
            count < EcommCategoriesShowcaseOptionPlugin.MIN_BLOCK_COUNT ||
            count > EcommCategoriesShowcaseOptionPlugin.MAX_BLOCK_COUNT
        ) {
            return;
        }

        let blocks = wrapper.querySelectorAll(".s_ecomm_categories_showcase_block");

        // Remove blocks if needed
        while (blocks.length > count) {
            const blockToRemove = blocks[blocks.length - 1];
            blockToRemove.remove();
            blocks = wrapper.querySelectorAll(".s_ecomm_categories_showcase_block");
        }

        // Add blocks if needed. Insert before the edit-mode placeholder so the
        // first block stays the wrapper's first child (important for the first
        // block larger option).
        const alertEl = wrapper.querySelector(".s_ecomm_categories_showcase_empty_alert");
        while (blocks.length < count) {
            const newBlock = renderToElement("website.s_ecomm_categories_showcase.new_block");
            wrapper.insertBefore(newBlock, alertEl);
            blocks = wrapper.querySelectorAll(".s_ecomm_categories_showcase_block");
        }
    }

    isApplied({ editingElement, value }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        if (!wrapper) {
            return false;
        }
        const currentCount = wrapper.querySelectorAll(".s_ecomm_categories_showcase_block").length;
        const targetCount = parseInt(value, 10);
        return !isNaN(targetCount) && currentCount === targetCount;
    }
}

export class SpacingToggleAction extends BuilderAction {
    static id = "spacingToggle";

    isApplied({ editingElement }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        return wrapper && wrapper.classList.contains(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
    }

    apply({ editingElement }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        if (!wrapper) {
            return;
        }

        const hasGap = wrapper.classList.contains(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
        wrapper.classList.toggle(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);

        // Set roundness based on new state
        const newRoundness = hasGap
            ? EcommCategoriesShowcaseOptionPlugin.NO_ROUNDNESS
            : EcommCategoriesShowcaseOptionPlugin.DEFAULT_ROUNDNESS;
        EcommCategoriesShowcaseOptionPlugin._updateBlocksRoundness(editingElement, newRoundness);
    }

    clean({ editingElement }) {
        const wrapper = editingElement.querySelector(".s_ecomm_categories_showcase_wrapper");
        if (wrapper) {
            wrapper.classList.remove(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
            EcommCategoriesShowcaseOptionPlugin._updateBlocksRoundness(
                editingElement,
                EcommCategoriesShowcaseOptionPlugin.NO_ROUNDNESS
            );
        }
    }
}

export class AddEcommCategoriesShowcaseBlockAction extends BuilderAction {
    static id = "addEcommCategoriesShowcaseBlock";
    static dependencies = ["builderOptions"];
    apply({ editingElement: el }) {
        const newBlockEl = renderToElement("website.s_ecomm_categories_showcase.new_block");
        const wrapperEl = el.querySelector(".s_ecomm_categories_showcase_wrapper");
        const alertEl = wrapperEl.querySelector(".s_ecomm_categories_showcase_empty_alert");
        wrapperEl.insertBefore(newBlockEl, alertEl);
        newBlockEl.scrollIntoView({ behavior: "smooth", block: "center" });
        this.dependencies.builderOptions.setNextTarget(newBlockEl);
    }
}

registry
    .category("website-plugins")
    .add(EcommCategoriesShowcaseOptionPlugin.id, EcommCategoriesShowcaseOptionPlugin);
