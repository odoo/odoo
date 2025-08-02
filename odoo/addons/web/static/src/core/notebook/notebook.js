/** @odoo-module **/

import { scrollTo } from "@web/core/utils/scrolling";

import {
    Component,
    onWillDestroy,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

/**
 * A notebook component that will render only the current page and allow
 * switching between its pages.
 *
 * You can also set pages using a template component. Use an array with
 * the `pages` props to do such rendering.
 *
 * Pages can also specify their index in the notebook.
 *
 *      e.g.:
 *          PageTemplate.template = xml`
                    <h1 t-esc="props.heading" />
                    <p t-esc="props.text" />`;

 *      `pages` could be:
 *      [
 *          {
 *              Component: PageTemplate,
 *              id: 'unique_id' // optional: can be given as defaultPage props to the notebook
 *              index: 1 // optional: page position in the notebook
 *              name: 'some_name' // optional
 *              title: "Some Title 1", // title displayed on the tab pane
 *              props: {
 *                  heading: "Page 1",
 *                  text: "Text Content 1",
 *              },
 *          },
 *          {
 *              Component: PageTemplate,
 *              title: "Some Title 2",
 *              props: {
 *                  heading: "Page 2",
 *                  text: "Text Content 2",
 *              },
 *          },
 *      ]
 *
 * <Notebook pages="pages">
 *    <t t-set-slot="Page Name 1" title="Some Title" isVisible="bool">
 *      <div>Page Content 1</div>
 *    </t>
 *    <t t-set-slot="Page Name 2" title="Some Title" isVisible="bool">
 *      <div>Page Content 2</div>
 *    </t>
 * </Notebook>
 *
 * @extends Component
 */

export class Notebook extends Component {
    setup() {
        this.activePane = useRef("activePane");
        this.anchorTarget = null;
        this.pages = this.computePages(this.props);
        this.state = useState({ currentPage: null });
        this.state.currentPage = this.computeActivePage(this.props.defaultPage, true);
        const onAnchorClicked = this.onAnchorClicked.bind(this);
        this.env.bus.addEventListener("SCROLLER:ANCHOR_LINK_CLICKED", onAnchorClicked);
        useEffect(
            () => {
                this.props.onPageUpdate(this.state.currentPage);
                if (this.anchorTarget) {
                    const matchingEl = this.activePane.el.querySelector(`#${this.anchorTarget}`);
                    scrollTo(matchingEl, { isAnchor: true });
                    this.anchorTarget = null;
                }
            },
            () => [this.state.currentPage]
        );
        onWillUpdateProps((nextProps) => {
            const activateDefault =
                this.props.defaultPage !== nextProps.defaultPage || !this.defaultVisible;
            this.pages = this.computePages(nextProps);
            this.state.currentPage = this.computeActivePage(nextProps.defaultPage, activateDefault);
        });
        onWillDestroy(() => {
            this.env.bus.removeEventListener("SCROLLER:ANCHOR_LINK_CLICKED", onAnchorClicked);
        });
    }

    get navItems() {
        return this.pages.filter((e) => e[1].isVisible);
    }

    get page() {
        const page = this.pages.find((e) => e[0] === this.state.currentPage)[1];
        return page.Component && page;
    }

    onAnchorClicked(ev) {
        if (!this.props.anchors) {
            return;
        }
        const id = ev.detail.detail.id.substring(1);
        if (this.props.anchors[id]) {
            if (this.state.currentPage !== this.props.anchors[id].target) {
                ev.preventDefault();
                ev.detail.detail.originalEv.preventDefault();
                this.anchorTarget = id;
                this.state.currentPage = this.props.anchors[id].target;
            }
        }
    }

    activatePage(pageIndex) {
        if (!this.disabledPages.includes(pageIndex)) {
            this.state.currentPage = pageIndex;
        }
    }

    computePages(props) {
        if (!props.slots && !props.pages) {
            return [];
        }
        if (props.pages) {
            for (const page of props.pages) {
                page.isVisible = true;
            }
        }
        this.disabledPages = [];
        const pages = [];
        const pagesWithIndex = [];
        for (const [k, v] of Object.entries({ ...props.slots, ...props.pages })) {
            const id = v.id || k;
            if (v.index) {
                pagesWithIndex.push([id, v]);
            } else {
                pages.push([id, v]);
            }
            if (v.isDisabled) {
                this.disabledPages.push(k);
            }
        }
        for (const page of pagesWithIndex) {
            pages.splice(page[1].index, 0, page);
        }
        return pages;
    }

    computeActivePage(defaultPage, activateDefault) {
        if (!this.pages.length) {
            return null;
        }
        const pages = this.pages.filter((e) => e[1].isVisible).map((e) => e[0]);

        if (defaultPage) {
            if (!pages.includes(defaultPage)) {
                this.defaultVisible = false;
            } else {
                this.defaultVisible = true;
                if (activateDefault) {
                    return defaultPage;
                }
            }
        }
        const current = this.state.currentPage;
        if (!current || (current && !pages.includes(current))) {
            return pages[0];
        }

        return current;
    }
}

Notebook.template = "web.Notebook";
Notebook.defaultProps = {
    className: "",
    orientation: "horizontal",
    onPageUpdate: () => {},
};
Notebook.props = {
    slots: { type: Object, optional: true },
    pages: { type: Object, optional: true },
    class: { optional: true },
    className: { type: String, optional: true },
    anchors: { type: Object, optional: true },
    defaultPage: { type: String, optional: true },
    orientation: { type: String, optional: true },
    icons: { type: Object, optional: true },
    onPageUpdate: { type: Function, optional: true },
};
