// @ts-check
/** @odoo-module native */

import {
    Component,
    onWillDestroy,
    onWillRender,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";

const log = makeLogger("web.components.notebook");

export class Notebook extends Component {
    static template = "web.Notebook";
    static defaultProps = {
        className: "",
        orientation: "horizontal",
        onPageUpdate: () => {},
        onWillActivatePage: () => {},
    };
    static props = {
        slots: { type: Object, optional: true },
        pages: { type: Array, element: Object, optional: true },
        class: { type: String, optional: true },
        className: { type: String, optional: true },
        defaultPage: { type: String, optional: true },
        orientation: { type: String, optional: true },
        icons: { type: Object, optional: true },
        onPageUpdate: { type: Function, optional: true },
        onWillActivatePage: { type: Function, optional: true },
        isFieldInvalid: { type: Function, optional: true },
    };

    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    activePane;
    /** @type {Array<[string, Object]>} */
    pages;
    /** @type {Set<string>} */
    invalidPages;
    /** @type {{ currentPage: string | null }} */
    state;
    /** @type {string[]} */
    disabledPages;
    /** @type {boolean | undefined} */
    defaultVisible;
    /** @type {KeepLast} */
    keepLastPageTransition;

    setup() {
        useLifecycleLog(log);
        /** @type {import("@odoo/owl").Ref<HTMLElement>} */
        this.activePane = useRef("activePane");
        this.readPages(this.props);
        /** @type {Set<string>} */
        this.invalidPages = new Set();
        this.state = useState({ currentPage: null });
        this.selectActivePage(this.props.defaultPage, true);
        this.keepLastPageTransition = new KeepLast({ rejectSuperseded: true });
        onWillDestroy(() => this.keepLastPageTransition.cancel());
        useEffect(
            () => {
                this.props.onPageUpdate(this.state.currentPage);
            },
            () => [this.state.currentPage],
        );
        useEffect(
            (pane) => {
                pane?.classList.add("show");
            },
            () => [this.activePane.el],
        );
        onWillRender(() => {
            this.computeInvalidPages();
        });
        onWillUpdateProps((nextProps) => {
            const currentPage = this.state.currentPage;
            const activateDefault =
                this.props.defaultPage !== nextProps.defaultPage ||
                !this.defaultVisible;
            this.readPages(nextProps);
            this.selectActivePage(nextProps.defaultPage, activateDefault);
            if (
                currentPage !== this.state.currentPage ||
                (activateDefault && nextProps.defaultPage && this.defaultVisible)
            ) {
                log.logic("cancel activation after page selection", () => ({
                    currentPage: this.state.currentPage,
                }));
                this.keepLastPageTransition.cancel();
            }
        });
    }

    /** @returns {Array<[string, Object]>} */
    get navItems() {
        return this.pages.filter((e) => e[1].isVisible);
    }

    /** @returns {Object | undefined} */
    get page() {
        const entry = this.pages.find((e) => e[0] === this.state.currentPage);
        if (!entry) {
            return undefined;
        }
        const page = entry[1];
        return page.Component ? page : undefined;
    }

    /** @param {string} pageId */
    async activatePage(pageId) {
        if (!this.canActivatePage(pageId)) {
            return;
        }
        if (this.state.currentPage === pageId) {
            log.logic("cancel activation on current page", () => ({ pageId }));
            this.keepLastPageTransition.cancel();
            return;
        }
        const prom = (async () => this.beforePageActivation(pageId))();
        let canProceed;
        try {
            canProceed = await this.keepLastPageTransition.add(prom);
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            throw error;
        }
        log.logic("activatePage", () => ({ pageId, canProceed }));
        if (canProceed !== false && this.canActivatePage(pageId)) {
            this.state.currentPage = pageId;
        }
    }

    /** @param {string} pageId */
    beforePageActivation(pageId) {
        return this.props.onWillActivatePage(pageId);
    }

    /** @param {string} pageId */
    canActivatePage(pageId) {
        return (
            this.pages.some(([id, page]) => id === pageId && page.isVisible) &&
            !this.disabledPages.includes(pageId)
        );
    }

    /** @param {Object} props */
    readPages(props) {
        const { pages, disabledPages } = this.computePages(props);
        this.pages = pages;
        this.disabledPages = disabledPages;
    }

    /**
     * @param {Object} props
     * @returns {{ pages: Array<[string, Object]>, disabledPages: string[] }}
     */
    computePages(props) {
        /** @type {string[]} */
        const disabledPages = [];
        if (!props.slots && !props.pages) {
            return { pages: [], disabledPages };
        }
        /** @type {[string, any][]} */
        const pages = [];
        /** @type {[string, any][]} */
        const pagesWithIndex = [];
        const entries = [
            ...Object.entries(props.slots || {}),
            ...(props.pages || []).map(
                /** @returns {[string, any]} */
                (page, i) => [String(i), { ...page, isVisible: true }],
            ),
        ];
        for (const [k, v] of entries) {
            const id = v.id || k;
            if (v.index !== undefined) {
                pagesWithIndex.push([id, v]);
            } else {
                pages.push([id, v]);
            }
            if (v.isDisabled) {
                disabledPages.push(id);
            }
        }
        pagesWithIndex.sort((a, b) => a[1].index - b[1].index);
        for (const page of pagesWithIndex) {
            pages.splice(page[1].index, 0, page);
        }
        return { pages, disabledPages };
    }

    /**
     * @param {string | undefined} defaultPage
     * @param {boolean} activateDefault
     */
    selectActivePage(defaultPage, activateDefault) {
        if (!this.pages.length) {
            this.state.currentPage = null;
            return;
        }
        const pages = this.pages.filter((e) => e[1].isVisible).map((e) => e[0]);

        if (defaultPage) {
            this.defaultVisible = pages.includes(defaultPage);
            if (this.defaultVisible && activateDefault) {
                this.state.currentPage = defaultPage;
                return;
            }
        }
        const current = this.state.currentPage;
        this.state.currentPage =
            current && pages.includes(current) ? current : pages[0];
    }

    computeInvalidPages() {
        const isFieldInvalid = this.props.isFieldInvalid;
        if (!isFieldInvalid) {
            if (this.invalidPages.size) {
                this.invalidPages = new Set();
            }
            return;
        }
        const invalidPages = new Set();
        for (const [id, page] of this.navItems) {
            if (page.fieldNames?.some((fieldName) => isFieldInvalid(fieldName))) {
                invalidPages.add(id);
            }
        }
        this.invalidPages = invalidPages;
    }
}
