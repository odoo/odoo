import {
    containsAnyNonPhrasingContent,
    getDeepestPosition,
    isContentEditable,
    isElement,
    isEmpty,
    isMediaElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import {
    BASE_CONTAINER_CLASS,
    baseContainerGlobalSelector,
    createBaseContainer,
} from "../utils/base_container";
import { withSequence } from "@html_editor/utils/resource";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { childNodeIndex } from "@html_editor/utils/position";

/**
 * @typedef { Object } BaseContainerShared
 * @property { BaseContainerPlugin['createBaseContainer'] } createBaseContainer
 * @property { BaseContainerPlugin['getDefaultNodeName'] } getDefaultNodeName
 * @property { BaseContainerPlugin['isCandidateForBaseContainer'] } isCandidateForBaseContainer
 */

/**
 * @typedef {((node: Node) => boolean | undefined)[]} is_valid_for_base_container_predicates
 */

export class BaseContainerPlugin extends Plugin {
    static id = "baseContainer";
    static shared = ["createBaseContainer", "getDefaultNodeName", "isCandidateForBaseContainer"];
    static defaultConfig = {
        baseContainers: ["P", "DIV"],
    };
    static dependencies = ["selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        clean_for_save_processors: this.cleanForSave.bind(this),
        // `baseContainer` normalization should occur after every other normalization
        // because a `div` may only have the baseContainer identity if it does not
        // already have another incompatible identity given by another plugin.
        normalize_processors: withSequence(Infinity, this.normalizeDivBaseContainers.bind(this)),
        on_deleted_handlers: () => {
            if (this.config.cleanEmptyStructuralContainers === false) {
                return;
            }
            this.cleanEmptyStructuralContainers();
        },
        is_node_splittable_predicates: (node) => {
            if (
                node.nodeName === "DIV" &&
                !this.isCandidateForBaseContainerAllowUnsplittable(node)
            ) {
                return false;
            }
        },
        is_valid_for_base_container_predicates: [
            (node) => {
                if (
                    !node ||
                    node.nodeType !== Node.ELEMENT_NODE ||
                    !this.config.baseContainers.includes(node.tagName) ||
                    isProtected(node) ||
                    isProtecting(node) ||
                    isMediaElement(node)
                ) {
                    return false;
                }
            },
            (element, options) => {
                if (
                    !options?.allowUnsplittable &&
                    !(this.checkPredicates("is_node_splittable_predicates", element) ?? true)
                ) {
                    return false;
                }
            },
            (element, options) => {
                if (
                    !options?.shallow &&
                    element?.nodeType === Node.ELEMENT_NODE &&
                    containsAnyNonPhrasingContent(element)
                ) {
                    return false;
                }
            },
        ],
        system_classes: [BASE_CONTAINER_CLASS],
    };

    createBaseContainer(nodeName = this.getDefaultNodeName()) {
        return createBaseContainer(nodeName, this.document);
    }

    getDefaultNodeName() {
        return this.config.baseContainers[0];
    }

    cleanEmptyStructuralContainers() {
        const node = this.document.getSelection().anchorNode;

        if (!isElement(node) || !isEmpty(node)) {
            return;
        }

        const closestEditable = (n) =>
            isContentEditable(n.parentElement) ? closestEditable(n.parentElement) : n;

        const isUnsplittable = !(this.checkPredicates("is_node_splittable_predicates", node) ?? true);
        const isCandidateForBase = this.isCandidateForBaseContainerAllowUnsplittable(node);

        if (isUnsplittable || !isCandidateForBase) {
            return;
        }

        let anchorNode = node.parentElement;
        if (
            anchorNode === closestEditable(node) ||
            !this.config.baseContainers.includes(anchorNode.nodeName) ||
            !(this.checkPredicates("is_node_removable_predicates", anchorNode) ?? true)
        ) {
            return;
        }

        if (isEmpty(anchorNode)) {
            fillEmpty(anchorNode);
        }

        let anchorOffset = childNodeIndex(node);
        node.remove();

        [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
        });
    }

    /**
     * Evaluate if an element is eligible to become a baseContainer (i.e. an
     * unmarked div which could receive baseContainer attributes to inherit
     * paragraph-like features).
     *
     * This function considers unsplittable and childNodes.
     */
    isCandidateForBaseContainer(element) {
        return this.checkPredicates("is_valid_for_base_container_predicates", element) ?? true;
    }

    /**
     * Evaluate if an element would be eligible to become a baseContainer
     * without considering unsplittable.
     *
     * This function is only meant to be used during `is_node_splittable_predicates` to
     * avoid an infinite loop:
     * Considering a `DIV`,
     * - During `is_node_splittable_predicates`, one predicate should return false
     *   if the `DIV` is NOT a baseContainer candidate (Odoo specification),
     *   therefore `is_valid_for_base_container_predicates` should be evaluated.
     * - During `is_valid_for_base_container_predicates`, one predicate should
     *   return false if the `DIV` is unsplittable, because a node has to be
     *   splittable to use the featureSet associated with paragraphs.
     * Each resource has to call the other. To avoid the issue, during
     * `is_node_splittable_predicates`, the baseContainer predicate will execute
     * all predicates for `is_valid_for_base_container_predicates` except the one
     * using `is_node_splittable_predicates`, since it is already being evaluated.
     *
     * In simpler terms:
     * A `DIV` is unsplittable by default;
     * UNLESS it is eligible to be a baseContainer => it becomes one;
     * UNLESS it has to be unsplittable for an explicit reason (i.e. has class
     * oe_unbreakable) => it stays unsplittable.
     */
    isCandidateForBaseContainerAllowUnsplittable(element) {
        return (
            this.checkPredicates("is_valid_for_base_container_predicates", element, {
                allowUnsplittable: true,
            }) ?? true
        );
    }

    /**
     * Evaluate if an element would be eligible to become a baseContainer
     * without considering its childNodes.
     *
     * This function is only meant to be used internally, to avoid having to
     * compute childNodes multiple times in more complex operations.
     */
    shallowIsCandidateForBaseContainer(element) {
        return (
            this.checkPredicates("is_valid_for_base_container_predicates", element, {
                shallow: true,
            }) ?? true
        );
    }

    cleanForSave(root) {
        for (const baseContainer of selectElements(root, `.${BASE_CONTAINER_CLASS}`)) {
            baseContainer.classList.remove(BASE_CONTAINER_CLASS);
            if (baseContainer.classList.length === 0) {
                baseContainer.removeAttribute("class");
            }
        }
    }

    normalizeDivBaseContainers(element = this.editable) {
        if (this.config.baseContainers && !this.config.baseContainers.includes("DIV")) {
            return;
        }
        const newBaseContainers = [];
        const divSelector = `div:not(.${BASE_CONTAINER_CLASS})`;
        const targets = [...element.querySelectorAll(divSelector)];
        if (element.matches(divSelector)) {
            targets.unshift(element);
        }
        for (const div of targets) {
            if (
                // Ensure that newly created `div` baseContainers are never themselves
                // children of a baseContainer. BaseContainers should always only
                // contain phrasing content (even `div`), because they could be
                // converted to an element which can actually only contain phrasing
                // content. In practice a div should never be a child of a
                // baseContainer, since a baseContainer should only contain
                // phrasingContent.
                !div.parentElement?.matches(baseContainerGlobalSelector) &&
                this.shallowIsCandidateForBaseContainer(div) &&
                !containsAnyNonPhrasingContent(div)
            ) {
                div.classList.add(BASE_CONTAINER_CLASS);
                newBaseContainers.push(div);
                fillEmpty(div);
            }
        }
    }
}
