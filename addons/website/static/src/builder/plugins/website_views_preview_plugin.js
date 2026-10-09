import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ASSETS, VIEWS } from "./customize_website_plugin";

/**
 * @typedef { Object } WebsiteViewsPreviewShared
 * @property { WebsiteViewsPreviewPlugin['previewViews'] } previewViews
 */

/**
 * @typedef {((parts: { oldEl: HTMLElement, newEl: HTMLElement }) => void)[]} on_chrome_replaced_handlers
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
        ...["customizeWebsite", "themeComputedPreview", "domObserver", "dom", "domReferenceMap"],
        ...["setup_editor_plugin", "builderOptions", "edit_interaction"],
    ];
    static shared = ["previewViews"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_theme_preview_changed_handlers: () => this.updateChrome(),
    };

    /** @type {Object<string, Promise>} the page's renders, by previewed views */
    chromeRenders = {};
    /** @type {Object<string, HTMLElement>} the elements a views switch took out, by render */
    chromeElements = {};
    /** The previewed views the page shows (see `updateChrome`). */
    chromeKey = "{}";
    chromeRequestId = 0;
    /** @type {Promise|null} the scheduled `updateChrome` */
    chromeUpdate = null;
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
        this.dependencies.customizeWebsite.previewPendingValues(areAssets ? ASSETS : VIEWS, views);
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
        return (this.chromeUpdate ??= new Promise((resolve) =>
            setTimeout(() => {
                this.chromeUpdate = null;
                resolve(this._updateChrome());
            })
        ));
    }
    async _updateChrome() {
        const { getPendingViews, getSavedConfigKey } = this.dependencies.customizeWebsite;
        const views = Object.entries(getPendingViews())
            .map(([view, pending]) => [view, pending === true])
            // Unknown saved state: kept, the server knows.
            .filter(([view, active]) => active !== getSavedConfigKey(view));
        const key = JSON.stringify(Object.fromEntries(views.sort()));
        const requestId = ++this.chromeRequestId;
        // The views the page shows by itself need no render, but are part of
        // the renders' key: a render shows them too.
        const withoutShown = (viewsKey) =>
            JSON.stringify(
                Object.entries(JSON.parse(viewsKey)).filter(([view]) => !this.shownViews.has(view))
            );
        if (withoutShown(key) === withoutShown(this.chromeKey)) {
            this.chromeKey = key;
            return;
        }
        // The page's content is only swapped for its own views: its render is
        // never quite the same (tokens...).
        const pageKey = (viewsKey) =>
            JSON.stringify(
                Object.entries(JSON.parse(viewsKey)).filter(([view]) => this.pageViews.has(view))
            );
        const [fromPageKey, toPageKey] = [pageKey(this.chromeKey), pageKey(key)];
        const wrapwrapEl = this.document.getElementById("wrapwrap");
        const parts = ["header#top", "footer#bottom"];
        if (fromPageKey !== toPageKey) {
            parts.push("main");
        }
        const targetEl = this.dependencies.builderOptions.getTarget();
        let loadingEls = [];
        if (!(this.chromeKey in this.chromeRenders && key in this.chromeRenders)) {
            // The part being edited (else both) shows that it's on its way.
            const partEls = parts.map((part) => wrapwrapEl.querySelector(`:scope > ${part}`));
            loadingEls = partEls.filter((el) => el?.contains(targetEl));
            loadingEls = loadingEls.length ? loadingEls : partEls.filter(Boolean);
            this.dependencies.domObserver.ignore(() => {
                loadingEls.forEach((el) => el.classList.add("o_we_chrome_loading"));
            });
        }
        let from, to;
        try {
            [from, to] = await Promise.all(
                [this.chromeKey, key].map((viewsKey) => this.getChromeRender(viewsKey))
            );
        } finally {
            this.dependencies.domObserver.ignore(() => {
                loadingEls.forEach((el) => el.classList.remove("o_we_chrome_loading"));
            });
        }
        if (requestId !== this.chromeRequestId || this.isDestroyed) {
            return;
        }
        let mainEl = wrapwrapEl.querySelector(":scope > main");
        let newTargetEl;
        // The options of the parts taken out go to their counterparts, so that
        // the panel is updated rather than rebuilt (see `builderOptions`).
        const replacements = new Map();
        this.dependencies.domObserver.ignore(() => {
            for (const [part, insert] of [
                [
                    "main",
                    (el) => {
                        mainEl.before(el);
                        mainEl.remove();
                    },
                ],
                ["header#top", (el) => mainEl.before(el)],
                ["footer#bottom", (el) => mainEl.after(el)],
            ]) {
                if (!parts.includes(part)) {
                    continue;
                }
                // Only a part rendered differently is replaced, and the live
                // element is kept for when that render shows again (the
                // page's content: by its views).
                let [fromKey, toKey] = [from[part]?.outerHTML || "", to[part]?.outerHTML || ""];
                if (part === "main") {
                    [fromKey, toKey] = [`main ${fromPageKey}`, `main ${toPageKey}`];
                } else if (fromKey === toKey) {
                    continue;
                }
                const currentEl = wrapwrapEl.querySelector(`:scope > ${part}`);
                const nextEl =
                    this.chromeElements[toKey] ||
                    (to[part] && this.document.importNode(to[part], true));
                this.chromeElements[fromKey] = currentEl;
                delete this.chromeElements[toKey];
                const hadTarget = !!currentEl?.contains(targetEl);
                if (currentEl && nextEl) {
                    this.carryEdits(currentEl, nextEl);
                    for (const { element } of this.dependencies.builderOptions.getContainers()) {
                        const counterpartEl =
                            currentEl.contains(element) &&
                            findCounterpart(element, currentEl, nextEl, part === "main");
                        if (counterpartEl) {
                            replacements.set(element, counterpartEl);
                        }
                    }
                }
                if (part === "main") {
                    insert(nextEl);
                    mainEl = nextEl;
                } else {
                    currentEl?.remove();
                    if (nextEl) {
                        insert(nextEl);
                    }
                }
                if (hadTarget && !targetEl.isConnected) {
                    // The options were on the part taken out: on the new one.
                    newTargetEl =
                        (nextEl && findCounterpart(targetEl, currentEl, nextEl, part === "main")) ||
                        nextEl;
                }
                if (nextEl) {
                    // Inserted unobserved: known from now on, so that its
                    // edits are recorded (undo, save).
                    this.dependencies.domReferenceMap.register(nextEl);
                    this.dependencies.setup_editor_plugin.markSavableAreas(nextEl);
                    this.dependencies.dom.normalize(nextEl);
                    if (currentEl) {
                        this.trigger("on_chrome_replaced_handlers", {
                            oldEl: currentEl,
                            newEl: nextEl,
                        });
                    }
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
        this.chromeKey = key;
        // A new part shows the previewed area presets too.
        this.dependencies.themeComputedPreview.updateAreaClasses();
        if (newTargetEl || replacements.size) {
            this.dependencies.builderOptions.replaceContainerElements(replacements);
            this.dependencies.builderOptions.updateContainers(newTargetEl);
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
     * @returns {Promise<Object>} the page's header, footer and root classes,
     *          as rendered with them
     */
    getChromeRender(key) {
        this.chromeRenders[key] ??= (async () => {
            const { pathname, search } = this.document.defaultView.location;
            const url = new URL(pathname + search, window.location.origin);
            url.searchParams.set("theme_preview_views", key);
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`The page's render failed (${response.status})`);
            }
            const doc = new DOMParser().parseFromString(await response.text(), "text/html");
            const classes = {};
            for (const selector of ["html", "body", "#wrapwrap"]) {
                classes[selector] = [...(doc.querySelector(selector)?.classList || [])];
            }
            return {
                "header#top": doc.querySelector("#wrapwrap > header#top"),
                "footer#bottom": doc.querySelector("#wrapwrap > footer#bottom"),
                main: doc.querySelector("#wrapwrap > main"),
                classes,
            };
        })().catch((error) => {
            delete this.chromeRenders[key];
            throw error;
        });
        return this.chromeRenders[key];
    }
}

registry.category("website-plugins").add(WebsiteViewsPreviewPlugin.id, WebsiteViewsPreviewPlugin);
