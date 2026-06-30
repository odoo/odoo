import {
    Component,
    computed,
    signal,
    useEffect,
    types as t,
    onWillUpdateProps,
    onPatched,
    onMounted,
} from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

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
                    <h1 t-out="this.props.heading" />
                    <p t-out="this.props.text" />`;

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

export const notebookProps = {
    slots: t.object().optional(),
    pages: t.array().optional(),
    class: t.any().optional(),
    className: t.string().optional(""),
    defaultPage: t.string().optional(),
    orientation: t.string().optional("horizontal"),
    icons: t.object().optional(),
    onPageUpdate: t.function().optional(() => () => {}),
    onWillActivatePage: t.function().optional(() => () => {}),
};

export class Notebook extends Component {
    static template = "web.Notebook";
    props = props(notebookProps);

    activePaneRef = signal(null, { type: t.ref() });
    pages = signal([]);
    currentPage = signal(null);

    navItems = computed(() => this.pages().filter((e) => e[1].isVisible));
    page = computed(() => {
        const found = this.pages().find((e) => e[0] === this.currentPage());
        return found?.[1]?.Component && found[1];
    });
    invalidPages = computed(() => this.computeInvalidPages());

    setup() {
        this.pages.set(this.computePages(this.props));
        this.currentPage.set(this.computeActivePage(this.props.defaultPage, true));
        this.keepLastPageTransition = new KeepLast();

        onMounted(() => {
            this.props.onPageUpdate(this.currentPage());
        });
        onPatched(() => {
            this.props.onPageUpdate(this.currentPage());
        });
        useEffect(() => {
            const page = this.currentPage();
            const ref = this.activePaneRef();
            if (ref && page) {
                ref.classList.add("show");
            }
        });

        onWillUpdateProps((nextProps) => {
            const activateDefault =
                this.props.defaultPage !== nextProps.defaultPage || !this.defaultVisible;
            this.pages.set(this.computePages(nextProps));
            const newPage = this.computeActivePage(nextProps.defaultPage, activateDefault);
            this.currentPage.set(newPage);
        });
    }

    async activatePage(pageIndex) {
        if (!this.disabledPages.includes(pageIndex) && this.currentPage() !== pageIndex) {
            const prom = (async () => this.props.onWillActivatePage(pageIndex))();
            const canProceed = await this.keepLastPageTransition.add(prom);
            if (canProceed !== false) {
                this.activePaneRef()?.classList.remove("show");
                this.currentPage.set(pageIndex);
            }
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
        if (!this.pages().length) {
            return null;
        }
        const pages = this.pages()
            .filter((e) => e[1].isVisible)
            .map((e) => e[0]);

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
        const current = this.currentPage?.();
        if (!current || (current && !pages.includes(current))) {
            return pages[0];
        }

        return current;
    }

    computeInvalidPages() {
        const result = new Set();
        for (const page of this.navItems()) {
            const invalid = page[1].fieldNames?.some((fieldName) =>
                this.env.model?.root.isFieldInvalid(fieldName)
            );
            if (invalid) {
                result.add(page[0]);
            }
        }
        return result;
    }
}
