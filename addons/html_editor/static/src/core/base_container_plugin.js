import {
    containsAnyNonPhrasingContent,
    isMediaElement,
    isProtected,
    isProtecting,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import {
    BASE_CONTAINER_CLASS,
    SUPPORTED_BASE_CONTAINER_NAMES,
    baseContainerGlobalSelector,
    createBaseContainer,
} from "../utils/base_container";
import { withSequence } from "@html_editor/utils/resource";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class BaseContainerPlugin extends Plugin {
    static id = "baseContainer";
    static shared = ["createBaseContainer", "getDefaultNodeName", "isCandidateForBaseContainer"];
    /**
     * Register one of the predicates for `invalid_for_base_container_predicates`
     * as a property for optimization, see variants of `isCandidateForBaseContainer`.
     */
    hasNonPhrasingContentPredicate = (element) => {
        return element?.nodeType === Node.ELEMENT_NODE && containsAnyNonPhrasingContent(element);
    };
    /**
     * The `unsplittable` predicate for `invalid_for_base_container_predicates`
     * is defined in this file and not in split_plugin because it has to be removed
     * in a specific case: see `isCandidateForBaseContainerAllowUnsplittable`.
     */
    isUnsplittablePredicate = (element) => {
        return this.getResource("unsplittable_node_predicates").some((fn) => fn(element));
    };
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        // `baseContainer` normalization should occur after every other normalization
        // because a `div` may only have the baseContainer identity if it does not
        // already have another incompatible identity given by another plugin.
        normalize_handlers: withSequence(Infinity, this.normalizeDivBaseContainers.bind(this)),
        unsplittable_node_predicates: (node) => {
            if (node.nodeName !== "DIV") {
                return false;
            }
            return !this.isCandidateForBaseContainerAllowUnsplittable(node);
        },
        invalid_for_base_container_predicates: [
            (node) =>
                !node ||
                node.nodeType !== Node.ELEMENT_NODE ||
                !SUPPORTED_BASE_CONTAINER_NAMES.includes(node.tagName) ||
                isProtected(node) ||
                isProtecting(node) ||
                isMediaElement(node),
            this.isUnsplittablePredicate,
            this.hasNonPhrasingContentPredicate,
        ],
        system_classes: [BASE_CONTAINER_CLASS],
    };

    createBaseContainer(nodeName = this.getDefaultNodeName()) {
        return createBaseContainer(nodeName, this.document);
    }

    getDefaultNodeName() {
        return this.config.baseContainer || "P";
    }

    /**
     * Evaluate if an element is eligible to become a baseContainer (i.e. an
     * unmarked div which could receive baseContainer attributes to inherit
     * paragraph-like features).
     *
     * This function considers unsplittable and childNodes.
     */
    isCandidateForBaseContainer(element) {
        return !this.getResource("invalid_for_base_container_predicates").some((fn) => fn(element));
    }

    /**
     * Evaluate if an element would be eligible to become a baseContainer
     * without considering unsplittable.
     *
     * This function is only meant to be used during `unsplittable_node_predicates` to
     * avoid an infinite loop:
     * Considering a `DIV`,
     * - During `unsplittable_node_predicates`, one predicate should return true
     *   if the `DIV` is NOT a baseContainer candidate (Odoo specification),
     *   therefore `invalid_for_base_container_predicates` should be evaluated.
     * - During `invalid_for_base_container_predicates`, one predicate should
     *   return true if the `DIV` is unsplittable, because a node has to be
     *   splittable to use the featureSet associated with paragraphs.
     * Each resource has to call the other. To avoid the issue, during
     * `unsplittable_node_predicates`, the baseContainer predicate will execute
     * all predicates for `invalid_for_base_container_predicates` except
     * the one using `unsplittable_node_predicates`, since it is already being
     * evaluated.
     *
     * In simpler terms:
     * A `DIV` is unsplittable by default;
     * UNLESS it is eligible to be a baseContainer => it becomes one;
     * UNLESS it has to be unsplittable for an explicit reason (i.e. has class
     * oe_unbreakable) => it stays unsplittable.
     */
    isCandidateForBaseContainerAllowUnsplittable(element) {
        const predicates = new Set(this.getResource("invalid_for_base_container_predicates"));
        predicates.delete(this.isUnsplittablePredicate);
        for (const predicate of predicates) {
            if (predicate(element)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Evaluate if an element would be eligible to become a baseContainer
     * without considering its childNodes.
     *
     * This function is only meant to be used internally, to avoid having to
     * compute childNodes multiple times in more complex operations.
     */
    shallowIsCandidateForBaseContainer(element) {
        const predicates = new Set(this.getResource("invalid_for_base_container_predicates"));
        predicates.delete(this.hasNonPhrasingContentPredicate);
        for (const predicate of predicates) {
            if (predicate(element)) {
                return false;
            }
        }
        return true;
    }

    cleanForSave({ root }) {
        for (const baseContainer of selectElements(root, `.${BASE_CONTAINER_CLASS}`)) {
            baseContainer.classList.remove(BASE_CONTAINER_CLASS);
            if (baseContainer.classList.length === 0) {
                baseContainer.removeAttribute("class");
            }
        }
    }

    normalizeDivBaseContainers(element = this.editable) {
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
