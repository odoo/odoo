import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_BEFORE, END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS, VERTICAL_ALIGNMENT } from "@website/builder/option_sequence";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { BuilderAction } from "@html_builder/core/builder_action";

class EcommCategoriesShowcaseOptionPlugin extends Plugin {
    static id = "ecommCategoriesShowcaseOption";
    static dependencies = ["history"];

    static DEFAULT_BLOCK_COUNT = 3;
    static MIN_BLOCK_COUNT = 2;
    static MAX_BLOCK_COUNT = 4;
    static GAP_CLASS = 'gap-4';
    static DEFAULT_ROUNDNESS = 'rounded-2';
    static NO_ROUNDNESS = 'rounded-0';
    static ROUNDNESS_CLASSES = ['rounded-0', 'rounded-1', 'rounded-2', 'rounded-3', 'rounded-4', 'rounded-5'];

    setup() {
        super.setup();
        // Store removed blocks per element to preserve user edits
        this.removedBlocksCache = new WeakMap();
    }

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, {
                template: "html_builder.EcommCategoriesShowcaseOption",
                selector: ".s_ecomm_categories_showcase",
            }),
            withSequence(WEBSITE_BACKGROUND_OPTIONS + 1, {
                OptionComponent: WebsiteBackgroundOption,
                selector: ".s_ecomm_categories_showcase_block",
                props: {
                    withColors: true,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(VERTICAL_ALIGNMENT, {
                template: "html_builder.EcommCategoriesShowcaseBlockDesign",
                selector: ".s_ecomm_categories_showcase_block",
            }),
            withSequence(END, {
                template: "html_builder.EcommCategoriesShowcaseBlocksDesign",
                selector: ".s_ecomm_categories_showcase",
            }),
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

    _updateBlocksRoundness(editingElement, roundnessClass) {
        const blocks = editingElement.querySelectorAll('.s_ecomm_categories_showcase_block');
        blocks.forEach(block => {
            block.classList.remove(...EcommCategoriesShowcaseOptionPlugin.ROUNDNESS_CLASSES);
            block.classList.add(roundnessClass);
        });
    }
}

class BlockCountAction extends BuilderAction {
    static id = "blockCount";
    static dependencies = ["history"];

    getValue({ editingElement }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        if (!wrapper) {
            return EcommCategoriesShowcaseOptionPlugin.DEFAULT_BLOCK_COUNT.toString();
        }
        return wrapper.querySelectorAll('.s_ecomm_categories_showcase_block').length.toString();
    }

    apply({ editingElement, value }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        if (!wrapper) {
            return;
        }

        const count = parseInt(value, 10);
        if (isNaN(count) || count < EcommCategoriesShowcaseOptionPlugin.MIN_BLOCK_COUNT || count > EcommCategoriesShowcaseOptionPlugin.MAX_BLOCK_COUNT) {
            return;
        }

        let blocks = wrapper.querySelectorAll('.s_ecomm_categories_showcase_block');
        const isPreview = this.dependencies.history.getIsPreviewing();
        
        // Since we can't easily access the plugin cache from here, we'll use a simpler approach
        // Store cache in the element's dataset
        if (!editingElement._removedBlocksCache) {
            editingElement._removedBlocksCache = [];
        }
        let removedBlocks = editingElement._removedBlocksCache;
        let workingRemovedBlocks = isPreview ? [...removedBlocks] : removedBlocks;

        // Remove blocks if needed
        while (blocks.length > count) {
            const blockToRemove = blocks[blocks.length - 1];
                        if (!isPreview) {
                workingRemovedBlocks.push(blockToRemove.cloneNode(true));
            }
            blockToRemove.remove();
            blocks = wrapper.querySelectorAll('.s_ecomm_categories_showcase_block');
        }

        // Add blocks if needed
        while (blocks.length < count) {
            if (workingRemovedBlocks.length > 0) {
                const restoredBlock = workingRemovedBlocks.pop();
                wrapper.appendChild(restoredBlock);
            } else {
                const newBlock = blocks[0].cloneNode(true);
                wrapper.appendChild(newBlock);
            }
            blocks = wrapper.querySelectorAll('.s_ecomm_categories_showcase_block');
        }

        if (!isPreview) {
            editingElement._removedBlocksCache = workingRemovedBlocks;
        }
    }

    isApplied({ editingElement, value }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        if (!wrapper) {
            return false;
        }
        const currentCount = wrapper.querySelectorAll('.s_ecomm_categories_showcase_block').length;
        const targetCount = parseInt(value, 10);
        return !isNaN(targetCount) && currentCount === targetCount;
    }
}

class SpacingToggleAction extends BuilderAction {
    static id = "spacingToggle";

    isApplied({ editingElement }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        return wrapper && wrapper.classList.contains(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
    }

    apply({ editingElement }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        if (!wrapper) {
            return;
        }
        
        const hasGap = wrapper.classList.contains(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
        wrapper.classList.toggle(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
        
        // Set roundness based on new state
        const newRoundness = hasGap ? EcommCategoriesShowcaseOptionPlugin.NO_ROUNDNESS : EcommCategoriesShowcaseOptionPlugin.DEFAULT_ROUNDNESS;
        this._updateBlocksRoundness(editingElement, newRoundness);
    }

    clean({ editingElement }) {
        const wrapper = editingElement.querySelector('.s_ecomm_categories_showcase_wrapper');
        if (wrapper) {
            wrapper.classList.remove(EcommCategoriesShowcaseOptionPlugin.GAP_CLASS);
            this._updateBlocksRoundness(editingElement, EcommCategoriesShowcaseOptionPlugin.NO_ROUNDNESS);
        }
    }

    _updateBlocksRoundness(editingElement, roundnessClass) {
        const blocks = editingElement.querySelectorAll('.s_ecomm_categories_showcase_block');
        blocks.forEach(block => {
            block.classList.remove(...EcommCategoriesShowcaseOptionPlugin.ROUNDNESS_CLASSES);
            block.classList.add(roundnessClass);
        });
    }
}

registry.category("website-plugins").add(EcommCategoriesShowcaseOptionPlugin.id, EcommCategoriesShowcaseOptionPlugin);
