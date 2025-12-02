import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import {
    SNIPPET_SPECIFIC_BEFORE,
    END,
    VERTICAL_ALIGNMENT,
} from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class EcommCategoriesShowcaseOption extends BaseOptionComponent {
    static template = "website.EcommCategoriesShowcaseOption";
    static selector = ".s_ecomm_categories_showcase";
}
export class EcommCategoriesShowcaseBlockDesign extends BaseOptionComponent {
    static template = "website.EcommCategoriesShowcaseBlockDesign";
    static selector = ".s_ecomm_categories_showcase_block";
}
export class EcommCategoriesShowcaseBlocksDesign extends BaseOptionComponent {
    static template = "website.EcommCategoriesShowcaseBlocksDesign";
    static selector = ".s_ecomm_categories_showcase";
}

class EcommCategoriesShowcaseOptionPlugin extends Plugin {
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
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, EcommCategoriesShowcaseOption),
            withSequence(VERTICAL_ALIGNMENT, EcommCategoriesShowcaseBlockDesign),
            withSequence(END, EcommCategoriesShowcaseBlocksDesign),
        ],
        builder_actions: {
            BlockCountAction,
            SpacingToggleAction,
        },
        dropzone_selector: {
            selector: ".s_ecomm_categories_showcase_block",
            dropNear: ".s_ecomm_categories_showcase_block",
        },
    };

    static _updateBlocksRoundness(editingElement, roundnessClass) {
        const blocks = editingElement.querySelectorAll(".s_ecomm_categories_showcase_block");
        blocks.forEach((block) => {
            block.classList.remove(...EcommCategoriesShowcaseOptionPlugin.ROUNDNESS_CLASSES);
            block.classList.add(roundnessClass);
        });
    }
}

class BlockCountAction extends BuilderAction {
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

        // Add blocks if needed
        while (blocks.length < count) {
            const newBlock = blocks[0].cloneNode(true);
            wrapper.appendChild(newBlock);
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

class SpacingToggleAction extends BuilderAction {
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

registry
    .category("website-plugins")
    .add(EcommCategoriesShowcaseOptionPlugin.id, EcommCategoriesShowcaseOptionPlugin);
