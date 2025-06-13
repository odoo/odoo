import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { listenSizeChange, utils as uiUtils } from "@web/core/ui/ui_service";
import { renderToFragment } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";


export class dynamicSnippetCategory extends Interaction {
    static selector = ".s_dynamic_category";

    async willStart() {
        const categoryId = this.el.dataset.categoryId;
        this.data = categoryId
            ? await this.waitFor(rpc('/shop/categories', { category_id: parseInt(categoryId) }))
            : [];
    }

    start() {
        this.registerCleanup(listenSizeChange(this.render.bind(this)));
        this.render();
    }

    render() {
        const nodeData = this.el.dataset;
        const SIZE_MAP = {
            small: { span: 2, row: "10vh" },
            medium: { span: 2, row: "15vh" },
            large: { span: 4, row: "15vh" },
        };
        const alignmentMap = {
            left: "justify-content-between",
            center: "align_category_center",
            right: "justify-content-between align_category_right",
        };
        const alignmentClass = alignmentMap[nodeData.alignment];

        // Clear existing content and render with new values
        const categoryGrid = this.el.querySelector('.s_category_container');
        const categoryWrapperEl = this.el.querySelector(".s_dynamic_category_wrapper");
        const categoryTemplate = nodeData?.isClickable
            ? "website_sale.dynamic_filter_template_categories_clickable_items"
            : "website_sale.dynamic_filter_template_categories";
        categoryWrapperEl.querySelectorAll(".category_item").forEach(el => {el.remove()});
        categoryWrapperEl.appendChild(
            renderToFragment(categoryTemplate, {
                data: this.data,
                size: SIZE_MAP[nodeData.size]['span'],
                alignmentClass: alignmentClass,
                buttonText: _t(nodeData.button),
            }
        ));

        // Styling for grid
        const columns = uiUtils.isSmall()? 1 : parseInt(nodeData.columns);
        categoryGrid.style.setProperty(
            '--DynamicCategory-columns', `${columns}`
        );
        categoryGrid.style.setProperty(
            'grid-auto-rows', `minmax(${SIZE_MAP[nodeData.size]['row']}, auto)`
        );

        // Styling for all_products item
        const allProducts = this.el.querySelector('.all_products');
        if (nodeData.allProducts === 'true') {
            allProducts.classList.remove('d-none');

            const overlay = allProducts.querySelector('.s_category_overlay');
            overlay.classList.remove(
                'justify-content-between',
                'align_category_right',
                'align_category_center'
            );
            overlay.className += " " + alignmentClass;

            const headingEl = allProducts.querySelector('.all_products_heading');
            headingEl.textContent = headingEl.textContent.trim() || "All Collections";

            allProducts.querySelector('a').textContent = nodeData.button;

            const shouldSpanTwo = columns !== 1 &&
                (['large', 'medium'].includes(nodeData.size) || columns === 5);
            allProducts.style.setProperty('grid-column', `span ${shouldSpanTwo ? 2 : 1}`);
            const allProductsButtonEl = allProducts.querySelector(".s_dynamic_category_button");
            const allProductsArrowEl = allProducts.querySelector(".s_dynamic_category_arrow");
            const allProductsImgEl = allProducts.querySelector(".s_category_image");
            const allProductsFilterEl = allProducts.querySelector(".s_category_filter");
            const allProductsOverlayEl = allProducts.querySelector(".s_category_overlay");
            const allProductsTitleEl = allProducts.querySelector("h3");
            const isClickable = Boolean(nodeData.isClickable);
            const toggleClass = (el, className, condition) => {
                el.classList.toggle(className, condition);
            }

            toggleClass(allProducts, "opacity-trigger-hover", isClickable);
            ["oe_unremovable", "stretched-link", "opacity-0", "p-0", "h-0"]
                .forEach(className => toggleClass(allProductsButtonEl, className, isClickable));
            toggleClass(allProductsArrowEl, "d-none", !isClickable);
            toggleClass(allProductsImgEl, "transition-base", isClickable);
            toggleClass(allProductsFilterEl, "d-none", !isClickable);
            toggleClass(allProductsOverlayEl, "z-0", isClickable);
            toggleClass(allProductsTitleEl, "mb-0", isClickable);
        } else {
            allProducts.classList.add("d-none");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale.dynamic_snippet_category", dynamicSnippetCategory);

registry
    .category("public.interactions.edit")
    .add("website_sale.dynamic_snippet_category", {Interaction: dynamicSnippetCategory});
