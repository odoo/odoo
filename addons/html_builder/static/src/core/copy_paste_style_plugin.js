import { getSnippetName } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef { Object } CopyPasteStyleShared
 * @property { CopyPasteStylePlugin['registerStyleItem'] } registerStyleItem
 * @property { CopyPasteStylePlugin['unregisterStyleItem'] } unregisterStyleItem
 */

/**
 * @typedef {String[][]} copy_style_excluded_actions
 * Ids of builder actions that must never be captured by "Copy styling", e.g.
 * actions carrying content rather than styling.
 *
 * @typedef {Object} StyleItem
 * A builder component bound to at least one builder action, as registered by
 * `useStyleItemRegistration`.
 * @property {() => {actionId: string, actionParam: Object, actionValue: any}[]} getAllActions
 * @property {() => HTMLElement[]} getEditingElements
 * @property {import("./dependency_manager").DependencyManager} dependencyManager
 * @property {Object} [selectableContext]
 */

const STORAGE_KEY = "html_builder.copied_styles";
const PAYLOAD_VERSION = 1;

/**
 * Key-order independent serialization, so that the identity of an action does
 * not depend on the order its params were declared in.
 *
 * @param {any} value
 * @returns {String}
 */
function stableStringify(value) {
    if (value === undefined) {
        return "";
    }
    if (value === null || typeof value !== "object") {
        return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
        return `[${value.map(stableStringify).join(",")}]`;
    }
    return `{${Object.keys(value)
        .sort()
        .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
        .join(",")}}`;
}

/**
 * Locates `el` inside `rootEl` as a path of child indexes, so that the same
 * position can be resolved on another instance of the same snippet. Options
 * routinely target a descendant of the block through `applyTo` (background on
 * `.container`, shapes on a child `div`, ...).
 *
 * @param {HTMLElement} rootEl
 * @param {HTMLElement} el
 * @returns {String|null} "" for `rootEl` itself, null when `el` is outside it
 */
function getRelativePath(rootEl, el) {
    const path = [];
    let currentEl = el;
    while (currentEl && currentEl !== rootEl) {
        const parentEl = currentEl.parentElement;
        if (!parentEl) {
            return null;
        }
        path.unshift([...parentEl.children].indexOf(currentEl));
        currentEl = parentEl;
    }
    return currentEl === rootEl ? path.join("/") : null;
}

/**
 * Copies the styling of a block and re-applies it on another one, on the same
 * page or on any other page.
 *
 * What gets copied is not the raw DOM state of the block but the state of the
 * options the builder exposes for it: each builder item knows its action, its
 * (post-`applyTo`) editing element and how to read itself back (`getValue` for
 * inputs, `isApplied` for clickables). Capturing that is styling-only by
 * construction - content, structural classes and identity attributes have no
 * option behind them - and matching the copied items against the *target's*
 * own items means a different kind of block simply receives the subset both
 * blocks can express.
 */
export class CopyPasteStylePlugin extends Plugin {
    static id = "copyPasteStyle";
    static dependencies = ["builderOptions", "builderActions"];
    static shared = ["registerStyleItem", "unregisterStyleItem"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        options_container_top_buttons_providers: withSequence(
            2,
            this.getOptionsContainerTopButtons.bind(this)
        ),
    };

    setup() {
        /** @type {Set<StyleItem>} */
        this.styleItems = new Set();
        this.excludedActionIds = new Set(this.getResource("copy_style_excluded_actions").flat());
        // Page-level containers are not blocks: their styling is website
        // configuration, not something to carry over to another element.
        this.excludedContainerSelector = "#wrapwrap, #wrapwrap > main";
    }

    /**
     * @param {StyleItem} styleItem
     */
    registerStyleItem(styleItem) {
        this.styleItems.add(styleItem);
    }

    /**
     * @param {StyleItem} styleItem
     */
    unregisterStyleItem(styleItem) {
        this.styleItems.delete(styleItem);
    }

    getOptionsContainerTopButtons(el) {
        if (el.matches(this.excludedContainerSelector)) {
            return [];
        }
        const buttons = [
            {
                class: "oi oi-fw o_hb_copy_styles btn o-hb-btn btn-global-color-hover",
                icon: "colorize",
                title: _t("Copy this block's styling"),
                handler: this.copyStyles.bind(this),
            },
        ];
        const copiedStyles = this.getCopiedStyles();
        if (copiedStyles) {
            buttons.push({
                class: "oi oi-fw o_hb_paste_styles btn o-hb-btn btn-global-color-hover",
                icon: "brush",
                title: _t("Paste the styling copied from %s", copiedStyles.title),
                handler: this.pasteStyles.bind(this),
            });
        }
        return buttons;
    }

    /**
     * Collects the builder items currently registered for `rootEl` and its
     * descendants, keyed by an identity that is stable across two instances of
     * the same snippet.
     *
     * @param {HTMLElement} rootEl
     * @returns {Map<String, Object>}
     */
    collectStyleItems(rootEl) {
        const getAction = this.dependencies.builderActions.getAction;
        const items = new Map();
        for (const styleItem of this.styleItems) {
            let editingElements;
            let actions;
            try {
                editingElements = styleItem.getEditingElements();
                actions = styleItem.getAllActions();
            } catch {
                // A component being torn down can no longer describe itself.
                continue;
            }
            for (const editingElement of editingElements) {
                const relPath = getRelativePath(rootEl, editingElement);
                if (relPath === null) {
                    continue;
                }
                for (const { actionId, actionParam, actionValue } of actions) {
                    if (this.excludedActionIds.has(actionId)) {
                        continue;
                    }
                    let action;
                    try {
                        action = getAction(actionId);
                    } catch {
                        continue;
                    }
                    // Reload actions are website-wide settings, not styling.
                    if (action.reload) {
                        continue;
                    }
                    // An action that can neither be read back nor tested is an
                    // operation (add a slide, clone an item, ...), not a state.
                    const kind = action.has("getValue")
                        ? "value"
                        : action.has("isApplied")
                        ? "toggle"
                        : null;
                    if (!kind) {
                        continue;
                    }
                    const key = [
                        actionId,
                        stableStringify(actionParam),
                        stableStringify(actionValue),
                        relPath,
                    ].join("|");
                    // `BuilderSelect` renders its items twice (once in an
                    // always-mounted hidden node, once in the dropdown), so the
                    // same item can be registered twice.
                    if (items.has(key)) {
                        continue;
                    }
                    items.set(key, {
                        key,
                        actionId,
                        actionParam,
                        actionValue,
                        relPath,
                        kind,
                        action,
                        editingElement,
                        styleItem,
                    });
                }
            }
        }
        return items;
    }

    /**
     * Captures the styling of `el` into the copy buffer.
     *
     * @param {HTMLElement} el
     */
    async copyStyles(el) {
        await this.unfoldContainer(el);
        const items = [];
        for (const item of this.collectStyleItems(el).values()) {
            const { key, actionId, actionParam, relPath, kind, action, editingElement } = item;
            const entry = { key, actionId, actionParam, relPath, kind };
            try {
                if (kind === "value") {
                    // An input reads itself through its own formatting: its
                    // action's raw `getValue` is not what `apply` consumes.
                    const value = item.styleItem.getValue
                        ? item.styleItem.getValue(editingElement)
                        : action.getValue({ editingElement, params: actionParam });
                    if (value === undefined) {
                        continue;
                    }
                    entry.value = value;
                } else {
                    entry.applied = !!action.isApplied({
                        editingElement,
                        params: actionParam,
                        value: item.actionValue,
                    });
                }
            } catch {
                continue;
            }
            items.push(entry);
        }
        if (!items.length) {
            this.services.notification.add(_t("This block has no styling to copy."), {
                type: "warning",
            });
            return;
        }
        const payload = {
            version: PAYLOAD_VERSION,
            snippetKey: el.dataset.snippet || "",
            title: getSnippetName(el),
            items,
        };
        try {
            browser.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch {
            this.services.notification.add(_t("The styling could not be copied."), {
                type: "danger",
            });
            return;
        }
        this.services.notification.add(_t("Styling of %s copied", payload.title), {
            type: "success",
        });
        // Make the "Paste styling" button appear on the other containers,
        // without moving the selection: the copied container is not
        // necessarily the selected one.
        this.dependencies.builderOptions.updateContainers(
            this.dependencies.builderOptions.getTarget(),
            { forceUpdate: true }
        );
    }

    /**
     * Applies the copy buffer onto `el`, restricted to the options `el` can
     * itself express.
     *
     * @param {HTMLElement} el
     */
    async pasteStyles(el) {
        const copiedStyles = this.getCopiedStyles();
        if (!copiedStyles) {
            return;
        }
        await this.unfoldContainer(el);
        const sourceItemsByKey = new Map(copiedStyles.items.map((item) => [item.key, item]));
        const cleanSpecs = [];
        const applySpecs = [];
        for (const targetItem of this.collectStyleItems(el).values()) {
            const sourceItem = sourceItemsByKey.get(targetItem.key);
            if (!sourceItem || sourceItem.kind !== targetItem.kind) {
                continue;
            }
            const isClean = targetItem.kind === "toggle" && !sourceItem.applied;
            const spec = {
                action: targetItem.action,
                isClean,
                isPreviewing: false,
                editingElement: targetItem.editingElement,
                params: targetItem.actionParam,
                value: targetItem.kind === "value" ? sourceItem.value : targetItem.actionValue,
                dependencyManager: targetItem.styleItem.dependencyManager,
                selectableContext: targetItem.styleItem.selectableContext,
            };
            (isClean ? cleanSpecs : applySpecs).push(spec);
        }
        const matchedCount = cleanSpecs.length + applySpecs.length;
        if (!matchedCount) {
            this.services.notification.add(
                _t("None of the styling copied from %s applies to this block.", copiedStyles.title),
                { type: "warning" }
            );
            return;
        }
        // `load` is side-effect free by contract and must run before `apply`.
        await Promise.all(
            [...cleanSpecs, ...applySpecs].map(async (spec) => {
                if (!spec.action.has("load") || (spec.isClean && !spec.action.loadOnClean)) {
                    return;
                }
                spec.loadResult = await spec.action.load({
                    editingElement: spec.editingElement,
                    params: spec.params,
                    value: spec.value,
                });
            })
        );
        // Clean first: otherwise cleaning an item of a selectable group would
        // undo what a sibling of that same group just applied.
        // A paste fans out over many actions, some of them contributed by other
        // addons: one of them failing must not abort the rest of the paste.
        let failedCount = 0;
        const run = async (spec, method) => {
            try {
                await spec.action[method](spec);
            } catch (error) {
                failedCount++;
                console.warn(
                    `Could not paste the styling of the "${spec.action.constructor.id}" action.`,
                    error
                );
            }
        };
        for (const spec of cleanSpecs) {
            if (spec.action.has("clean")) {
                await run(spec, "clean");
            }
        }
        for (const spec of applySpecs) {
            await run(spec, "apply");
        }
        const appliedCount = matchedCount - failedCount;
        if (!appliedCount) {
            this.services.notification.add(_t("The styling could not be pasted on this block."), {
                type: "danger",
            });
            return;
        }
        const isSameSnippet = (copiedStyles.snippetKey || "") === (el.dataset.snippet || "");
        this.services.notification.add(
            isSameSnippet
                ? _t("Styling pasted")
                : _t("Pasted %(count)s styling option(s) from %(source)s", {
                      count: appliedCount,
                      source: copiedStyles.title,
                  }),
            { type: "success" }
        );
    }

    /**
     * The options of a folded container are not rendered, hence not registered:
     * unfold it and let the sidebar render them before reading them.
     *
     * @param {HTMLElement} el
     */
    async unfoldContainer(el) {
        const container = this.dependencies.builderOptions
            .getContainers()
            .find((c) => c.element === el);
        if (!container || !container.folded) {
            return;
        }
        container.folded = false;
        container.foldedIntent = false;
        for (let i = 0; i < 2; i++) {
            await new Promise((resolve) => browser.requestAnimationFrame(() => resolve()));
        }
    }

    /**
     * @returns {Object|null} the copy buffer, or null when there is none
     */
    getCopiedStyles() {
        let rawPayload;
        try {
            rawPayload = browser.localStorage.getItem(STORAGE_KEY);
        } catch {
            return null;
        }
        if (!rawPayload) {
            return null;
        }
        let payload;
        try {
            payload = JSON.parse(rawPayload);
        } catch {
            payload = null;
        }
        if (
            !payload ||
            payload.version !== PAYLOAD_VERSION ||
            !Array.isArray(payload.items) ||
            !payload.items.length
        ) {
            this.clearCopiedStyles();
            return null;
        }
        return payload;
    }

    clearCopiedStyles() {
        try {
            browser.localStorage.removeItem(STORAGE_KEY);
        } catch {
            // Nothing to clear.
        }
    }
}
