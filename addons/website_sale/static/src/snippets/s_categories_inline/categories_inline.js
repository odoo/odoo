import { markup } from "@odoo/owl";
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";


export class CategoriesInline extends DynamicSnippet {
    static selector = '.s_categories_inline';
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                "overflow-x-auto":
                    (this.el.dataset.layout === "listgroup" && Boolean(this.el.dataset.horizontal))
                    || (this.el.dataset.layout === "thumbnails" && this.el.dataset.format === "column"),
            }),
        },
        ".dynamic_snippet_template": {
            "t-att-class": () => ({
                "d-flex": this.el.dataset.layout === "thumbnails" && this.el.dataset.format === "column",
            }),
        },
    };

    setup(){
        super.setup();
        this.templateKey = 'website_sale.s_categories_inlines.wrap';
    }

    isConfigComplete() {
        return true;
    }

    async fetchData() {
        // Unlike dynamic_snippet this snippet does not rely on a website.snippet.filters record
        // for filtering the dynamic records. Here the the record to be displayed on the snippet
        // are selected by an editor option and categories are filtered based on the selected
        // option on the fly.
        const nodeData = this.el.dataset;
        const filterFragments = await this.waitFor(rpc(
            '/shop/get_categories',
            Object.assign({
                'category_id': parseInt(nodeData.filterId),
                'template_key': 'website_sale.s_categories_inline_template_' + nodeData.layout,
            },
                this.getRpcParameters(),
            )
        ));
        this.data = filterFragments.map(markup);
    }

    getRpcParameters(){
        const res = super.getRpcParameters();
        const nodeData = this.el.dataset;
        Object.assign(res, {
            show_parent: nodeData.filterId && nodeData.showParent,
        });
        return res;
    }

    async render() {
        await super.render();
        const snippetInnerEl = this.el.querySelector('.s_categories_inline_inner');
        const nodeData = this.el.dataset;
        const isListOrListGroup = nodeData.layout ==="list" || nodeData.layout ==="listgroup";

        // Applying utility classes on the inner snippet element with classAction method doesn't
        // seems to work as it's reinitialised each time we interact with editor options.
        // This is why whe have to handle these classes when rendering the snippet.

        // Alignments
        snippetInnerEl.classList.toggle("text-center", isListOrListGroup && nodeData.alignment === "center");
        snippetInnerEl.classList.toggle("text-end", isListOrListGroup && nodeData.alignment === "right");
        snippetInnerEl.classList.toggle("justify-content-center", nodeData.layout === "nav" && nodeData.alignment === "center");
        snippetInnerEl.classList.toggle("justify-content-end", nodeData.layout === "nav" && nodeData.alignment === "right");
        snippetInnerEl.classList.toggle("list-group-horizontal", nodeData.layout === "listgroup" && Boolean(nodeData.horizontal));

        //List-group
        snippetInnerEl.classList.toggle("list-group-flush", nodeData.layout === "listgroup" && Boolean(nodeData.borderless) && Boolean(!nodeData.horizontal));

        //Thumbnails
        if (nodeData.layout === "thumbnails") {
            const thumbnailItemEls = snippetInnerEl.querySelectorAll('.s_categories_inline_item');
            const thumbnailLabelClasses =
                nodeData.label === "inside"
                ? "position-absolute start-50 top-50 translate-middle mb-0 w-100 px-2 text-white text-truncate text-center opacity-0 opacity-100-hover transition-base"
                : "d-block w-100 p-2 text-center text-truncate";

            for (const thumbnailItemEl of thumbnailItemEls) {
                const thumbnailFilterEl = thumbnailItemEl.querySelector('.o_we_bg_filter');
                const thumbnailLabelEl = thumbnailItemEl.querySelector('.s_categories_inline_thumbnails_label');
                const thumbnailImglEl = thumbnailItemEl.querySelector('img');

                thumbnailItemEl.classList.toggle("flex-shrink-0", nodeData.format === "column");
                thumbnailItemEl.classList.toggle("overflow-hidden", nodeData.label === "inside");
                thumbnailItemEl.classList.toggle("shadow-sm", Boolean(nodeData.shadow) && nodeData.label === "inside");
                thumbnailFilterEl.classList.toggle("d-none", nodeData.label === "outside");
                thumbnailLabelEl.className = thumbnailLabelClasses;
                thumbnailImglEl.classList.toggle("w-100", nodeData.format === "grid");
                thumbnailImglEl.classList.toggle("shadow-sm", Boolean(nodeData.shadow) && nodeData.label === "outside");
            }

            snippetInnerEl.classList.toggle("grid", nodeData.format === "grid");
            snippetInnerEl.classList.toggle("d-flex", nodeData.format === "column");
            snippetInnerEl.classList.toggle("ms-auto", nodeData.format === "column" && nodeData.alignment === "right");
            snippetInnerEl.classList.toggle("mx-auto", nodeData.format === "column" && nodeData.alignment === "center");
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.categories_inline', CategoriesInline);

registry
    .category('public.interactions.edit')
    .add('website_sale.categories_inline', {Interaction: CategoriesInline});
