import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { registry } from "@web/core/registry";
import { ASSETS, VIEWS, WebsiteConfigAction } from "./customize_website_plugin";

/**
 * @typedef { Object } WebsiteViewsPreviewShared
 * @property { WebsiteViewsPreviewPlugin['previewViews'] } previewViews
 */

/**
 * @typedef {((parts: { oldEl: HTMLElement|null, newEl: HTMLElement }) => void)[]} on_chrome_replaced_handlers
 */

/**
 * @param {HTMLElement} el
 * @returns {string} a selector for the record field `el` shows, if any
 */
function getRecordFieldSelector(el) {
    return ["oe-model", "oe-id", "oe-field", "oe-xpath"]
        .filter((name) => el.hasAttribute(`data-${name}`))
        .map((name) => `[data-${name}="${CSS.escape(el.getAttribute(`data-${name}`))}"]`)
        .join("");
}
/**
 * @param {HTMLElement} el an element in `fromEl`
 * @param {HTMLElement} fromEl
 * @param {HTMLElement} toEl another render of `fromEl`
 * @param {boolean} [byPosition] else at the same position (only for renders
 *        of the same layout: between two header layouts, the same position is
 *        another element)
 * @returns {HTMLElement|null} the element of `toEl` that is `el`: same id, or
 *          same record field, or the only one of its kind (see below)
 */
function findCounterpart(el, fromEl, toEl, byPosition = false) {
    if (el === fromEl) {
        return toEl;
    }
    const selector = el.id ? `#${CSS.escape(el.id)}` : getRecordFieldSelector(el);
    if (selector) {
        return toEl.querySelector(selector);
    }
    // The only element of the same tag with most of `el`'s classes (the live
    // element has the render's, and the editor's), e.g. the copyright bar;
    // not one of several menu links.
    let candidateEls = [];
    let maxClasses = 0;
    for (const candidateEl of toEl.querySelectorAll(el.tagName)) {
        const classes = [...candidateEl.classList];
        if (classes.length && classes.every((cls) => el.classList.contains(cls))) {
            if (classes.length > maxClasses) {
                [candidateEls, maxClasses] = [[], classes.length];
            }
            if (classes.length === maxClasses) {
                candidateEls.push(candidateEl);
            }
        }
    }
    if (candidateEls.length === 1) {
        return candidateEls[0];
    }
    if (byPosition) {
        const path = [];
        for (; el !== fromEl; el = el.parentElement) {
            path.unshift([...el.parentElement.children].indexOf(el));
        }
        return path.reduce((el, index) => el?.children[index], toEl) || null;
    }
    return null;
}

/**
 * Views switched by the builder (header and footer layouts, their options...)
 * previewed without a reload: pending like the theme values (see
 * `customizeWebsite`), the page shows them as the server renders them.
 */
export class WebsiteViewsPreviewPlugin extends Plugin {
    static id = "websiteViewsPreview";
    static dependencies = [
        ...["customizeWebsite", "domObserver", "dom", "domReferenceMap", "setup_editor_plugin"],
        ...["builderOptions", "edit_interaction"],
    ];
    static shared = ["previewViews"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            PreviewWebsiteConfigAction,
            PreviewPageConfigAction,
            PreviewableWebsiteConfigAction,
        },
        on_theme_preview_changed_handlers: (state) => {
            if (Object.values(state).some(({ file }) => file === VIEWS)) {
                this.updateChrome();
            }
        },
        // A swap in progress ends before the page is saved (it restarts the
        // page's interactions). A failed one was reported when it failed.
        on_will_save_handlers: () => this.lastChromeUpdate?.catch(() => {}),
    };

    /** @type {Object<string, Promise<Object>>} the page's renders, by previewed views */
    chromeRenders = {};
    /** @type {Object<string, HTMLElement>} the parts a views switch took out, by render */
    chromeElements = {};
    /** @type {Object<string, boolean>} the previewed views the page shows (see `updateChrome`) */
    chromeViews = {};
    chromeRequestId = 0;
    /** @type {Promise|null} the scheduled `updateChrome` */
    chromeUpdate = null;
    /** @type {Promise|null} the latest `updateChrome`, scheduled or running */
    lastChromeUpdate = null;
    /** @type {Set<string>} views the page shows by itself (see `previewViews`) */
    shownViews = new Set();
    /** @type {Set<string>} views of the page's own content (see `previewViews`) */
    pageViews = new Set();

    /**
     * Previews views switched on or off, written on save: the page shows them
     * meanwhile (see `updateChrome`).
     *
     * @param {Object<string, boolean|"reset">} views by key, whether it is
     *        active ("reset": disabled, its arch reset on save)
     * @param {Object} [options]
     * @param {boolean} [options.areAssets] assets instead (nothing to show:
     *        they apply after save)
     * @param {boolean} [options.areShown] the caller shows the views itself
     *        (e.g. their class): no render needed for them
     * @param {boolean} [options.arePage] the views change the page's own
     *        content (its `main`), not only its header and footer
     * @returns {Promise} resolved once the page shows the views
     */
    previewViews(views, { areAssets = false, areShown = false, arePage = false } = {}) {
        for (const view of Object.keys(views)) {
            if (areShown) {
                this.shownViews.add(view);
            }
            if (arePage) {
                this.pageViews.add(view);
            }
        }
        const file = areAssets ? ASSETS : VIEWS;
        this.dependencies.customizeWebsite.previewStep(
            Object.fromEntries(
                Object.entries(views).map(([view, pending]) => [view, { file, pending }])
            )
        );
        return this.updateChrome();
    }
    /**
     * Shows the page's header and footer (and its `main`, for the views of
     * the page's content) as the server renders them with the previewed views
     * (`?theme_preview_views`, nothing is written), so that a views switch
     * needs no reload. The renders are cached by views; the elements a switch
     * takes out are kept, and come back on undo as they were. Unsaved edits
     * follow the live page (see `carryEdits`). Not part of the history:
     * follows the previewed views. Scheduled once per tick.
     *
     * @returns {Promise} resolved once the page shows the previewed views
     */
    updateChrome() {
        this.chromeUpdate ??= new Promise((resolve) =>
            setTimeout(() => {
                this.chromeUpdate = null;
                resolve(this._updateChrome());
            })
        );
        this.lastChromeUpdate = this.chromeUpdate;
        return this.chromeUpdate;
    }
    async _updateChrome() {
        const { getPendingValues, getSavedConfigKey } = this.dependencies.customizeWebsite;
        const views = Object.fromEntries(
            Object.entries(getPendingValues(VIEWS))
                .map(([view, pending]) => [view, pending === true])
                // Unknown saved state: kept, the server knows.
                .filter(([view, active]) => active !== getSavedConfigKey(view))
                .sort()
        );
        const requestId = ++this.chromeRequestId;
        const keyOf = (views, isKept) =>
            JSON.stringify(Object.entries(views).filter(([view]) => isKept(view)));
        // The views the page shows by itself need no render, but are part of
        // the renders' key: a render shows them too.
        const isRendered = (view) => !this.shownViews.has(view);
        if (keyOf(views, isRendered) === keyOf(this.chromeViews, isRendered)) {
            this.chromeViews = views;
            return;
        }
        // The page's content is only swapped for its own views: its render is
        // never quite the same (tokens...).
        const isPage = (view) => this.pageViews.has(view);
        const [fromPageKey, toPageKey] = [this.chromeViews, views].map((v) => keyOf(v, isPage));
        const parts = ["header#top", "footer#bottom"];
        if (fromPageKey !== toPageKey) {
            parts.push("main");
        }
        const wrapwrapEl = this.document.getElementById("wrapwrap");
        const [fromKey, toKey] = [this.chromeViews, views].map((v) => JSON.stringify(v));
        let loadingEls = [];
        if (!(fromKey in this.chromeRenders && toKey in this.chromeRenders)) {
            // The part being edited (else all) shows that it's on its way.
            const targetEl = this.dependencies.builderOptions.getTarget();
            const partEls = parts
                .map((part) => wrapwrapEl.querySelector(`:scope > ${part}`))
                .filter(Boolean);
            loadingEls = partEls.filter((el) => el.contains(targetEl));
            loadingEls = loadingEls.length ? loadingEls : partEls;
            this.dependencies.domObserver.ignore(() => {
                loadingEls.forEach((el) => el.classList.add("o_we_chrome_loading"));
            });
        }
        let from, to;
        try {
            [from, to] = await Promise.all(
                [fromKey, toKey].map((key) => this.getChromeRender(key))
            );
        } finally {
            this.dependencies.domObserver.ignore(() => {
                loadingEls.forEach((el) => el.classList.remove("o_we_chrome_loading"));
            });
        }
        if (requestId !== this.chromeRequestId || this.isDestroyed) {
            return;
        }
        // The options' element, as it is now that the page is rendered.
        const targetEl = this.dependencies.builderOptions.getTarget();
        let newTargetEl;
        // The options of the parts taken out go to their counterparts, so that
        // the panel is updated rather than rebuilt (see `builderOptions`).
        const replacements = new Map();
        this.dependencies.domObserver.ignore(() => {
            for (const part of parts) {
                // Only a part rendered differently is replaced, and the live
                // element is kept for when that render shows again (the
                // page's content: by its views).
                const isMain = part === "main";
                const [fromPartKey, toPartKey] = isMain
                    ? [`main ${fromPageKey}`, `main ${toPageKey}`]
                    : [from[part], to[part]];
                if (fromPartKey === toPartKey) {
                    continue;
                }
                const currentEl = wrapwrapEl.querySelector(`:scope > ${part}`);
                const nextEl =
                    this.chromeElements[toPartKey] ||
                    (to[part] && parseHTML(this.document, to[part]).firstElementChild);
                this.chromeElements[fromPartKey] = currentEl;
                delete this.chromeElements[toPartKey];
                const hadTarget = !!currentEl?.contains(targetEl);
                if (currentEl && nextEl) {
                    this.carryEdits(currentEl, nextEl);
                    for (const { element } of this.dependencies.builderOptions.getContainers()) {
                        const counterpartEl =
                            currentEl.contains(element) &&
                            findCounterpart(element, currentEl, nextEl, isMain);
                        if (counterpartEl) {
                            replacements.set(element, counterpartEl);
                        }
                    }
                }
                if (currentEl) {
                    if (nextEl) {
                        currentEl.before(nextEl);
                    }
                    currentEl.remove();
                } else if (nextEl) {
                    // A part the page didn't have: around its content.
                    const mainEl = wrapwrapEl.querySelector(":scope > main");
                    if (part === "footer#bottom") {
                        mainEl.after(nextEl);
                    } else {
                        mainEl.before(nextEl);
                    }
                }
                if (hadTarget && !targetEl.isConnected) {
                    // The options were on the part taken out: on the new one.
                    newTargetEl =
                        (nextEl && findCounterpart(targetEl, currentEl, nextEl, isMain)) || nextEl;
                }
                if (nextEl) {
                    // Inserted unobserved: known from now on, so that its
                    // edits are recorded (undo, save).
                    this.dependencies.domReferenceMap.register(nextEl);
                    this.dependencies.setup_editor_plugin.markSavableAreas(nextEl);
                    this.dependencies.dom.normalize(nextEl);
                    this.trigger("on_chrome_replaced_handlers", {
                        oldEl: currentEl,
                        newEl: nextEl,
                    });
                }
            }
            // Some views set classes on the page's root elements.
            for (const selector of ["html", "body", "#wrapwrap"]) {
                const [fromClasses, toClasses] = [from.classes[selector], to.classes[selector]];
                const el = this.document.querySelector(selector);
                el.classList.remove(...fromClasses.filter((c) => !toClasses.includes(c)));
                el.classList.add(...toClasses.filter((c) => !fromClasses.includes(c)));
            }
        });
        this.chromeViews = views;
        if (newTargetEl || replacements.size) {
            this.dependencies.builderOptions.updateContainers(newTargetEl, { replacements });
            // The options read their element once rendered with the new one.
            requestAnimationFrame(
                () => !this.isDestroyed && this.trigger("on_dom_updated_handlers")
            );
        }
        this.dependencies.edit_interaction.restartInteractions();
        // The page adapts a new header's menu (see `auto_hide_menu.js`).
        this.document.dispatchEvent(new Event("o_header_rendered"));
        this.trigger("on_dom_updated_handlers");
    }
    /**
     * Moves the unsaved edits of a part taken out to the part replacing it,
     * where the same record field is, in exchange for its unedited render (so
     * that they move back on undo): they are saved from the live page.
     *
     * @param {HTMLElement} fromEl
     * @param {HTMLElement} toEl
     */
    carryEdits(fromEl, toEl) {
        for (const dirtyEl of fromEl.querySelectorAll(".o_dirty[data-oe-model]")) {
            if (toEl.contains(dirtyEl)) {
                // Moved with an edited ancestor.
                continue;
            }
            const counterpartEl = toEl.querySelector(getRecordFieldSelector(dirtyEl));
            if (counterpartEl) {
                const markerNode = this.document.createComment("");
                dirtyEl.before(markerNode);
                counterpartEl.before(dirtyEl);
                markerNode.before(counterpartEl);
                markerNode.remove();
            }
        }
    }
    /**
     * @param {string} key the previewed views, as JSON
     * @returns {Promise<Object>} the page's header, footer and `main` (as
     *          HTML, "" if none) and root classes, as rendered with them
     */
    getChromeRender(key) {
        this.chromeRenders[key] ??= (async () => {
            const { pathname, search } = this.document.defaultView.location;
            const url = new URL(pathname + search, window.location.origin);
            url.searchParams.set("theme_preview_views", key);
            // Not only a success: an error page is rendered with its status.
            const response = await fetch(url);
            const doc = new DOMParser().parseFromString(await response.text(), "text/html");
            if (!doc.getElementById("wrapwrap")) {
                throw new Error(`The page's render failed (${response.status})`);
            }
            const render = { classes: {} };
            for (const part of ["header#top", "footer#bottom", "main"]) {
                render[part] = doc.querySelector(`#wrapwrap > ${part}`)?.outerHTML || "";
            }
            for (const selector of ["html", "body", "#wrapwrap"]) {
                render.classes[selector] = [...doc.querySelector(selector).classList];
            }
            return render;
        })().catch((error) => {
            delete this.chromeRenders[key];
            throw error;
        });
        return this.chromeRenders[key];
    }
}

/**
 * Same as `websiteConfig`, without the reload: the views and the variables
 * are previewed (see `previewViews`) and written on save.
 */
export class PreviewWebsiteConfigAction extends WebsiteConfigAction {
    static id = "previewWebsiteConfig";
    static dependencies = [...WebsiteConfigAction.dependencies, "websiteViewsPreview"];
    /** Whether the views are the page's own content's (see `previewViews`). */
    arePage = false;
    // Drop the parent's reload. No hover preview: a switch shows once the
    // server rendered it, which the apply waits for, however long it takes.
    setup() {
        this.preview = false;
        this.canTimeout = false;
    }
    _customizeVariables(variables, clean, previewValues) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            Object.fromEntries(
                Object.entries(variables).map(([name, value]) => [name, clean ? "" : value ?? ""])
            ),
            "null",
            previewValues
        );
    }
    _customizeThemeData(isViewData, shouldReset, toEnable, toDisable) {
        return this.dependencies.websiteViewsPreview.previewViews(
            {
                ...Object.fromEntries([...toEnable].map((view) => [view, true])),
                ...Object.fromEntries(
                    [...toDisable].map((view) => [view, shouldReset ? "reset" : false])
                ),
            },
            { areAssets: !isViewData, arePage: this.arePage }
        );
    }
}

/**
 * `previewWebsiteConfig` for the views of the page's own content: the page's
 * `main` is rendered again too (see `updateChrome`).
 */
export class PreviewPageConfigAction extends PreviewWebsiteConfigAction {
    static id = "previewPageConfig";
    arePage = true;
}

export class PreviewableWebsiteConfigAction extends BuilderAction {
    static id = "previewableWebsiteConfig";
    static dependencies = ["websiteViewsPreview"];
    getPriority({ params }) {
        return (params.previewClass || "")?.trim().split(/\s+/).filter(Boolean).length || 0;
    }
    isApplied({ editingElement: el, params }) {
        if (params.previewClass === undefined || params.previewClass === "") {
            return true;
        }
        return params.previewClass.split(/\s+/).every((cls) => el.classList.contains(cls));
    }
    apply({ editingElement: el, isPreviewing, params }) {
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
        if (!isPreviewing) {
            this.previewViews(params.views, true);
        }
    }
    clean({ editingElement: el, isPreviewing, params }) {
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.remove(cls));
        }
        if (!isPreviewing) {
            this.previewViews(params.views, false);
        }
    }
    /**
     * The class shows the views: they are written on save, and part of the
     * page's renders (see `websiteViewsPreview.previewViews`).
     *
     * @param {string[]} views
     * @param {boolean} active
     */
    previewViews(views = [], active) {
        this.dependencies.websiteViewsPreview.previewViews(
            Object.fromEntries(
                views.map((view) =>
                    view.startsWith("!") ? [view.slice(1), !active] : [view, active]
                )
            ),
            { areShown: true }
        );
    }
}

registry.category("website-plugins").add(WebsiteViewsPreviewPlugin.id, WebsiteViewsPreviewPlugin);
