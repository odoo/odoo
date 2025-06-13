import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { listenSizeChange, utils as uiUtils } from "@web/core/ui/ui_service";
import { renderToFragment } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";


export class dynamicCategorySnippet extends Interaction{
    static selector = ".s_dynamic_category";

    async willStart() {
        this.ribbons = await this.waitFor(rpc('/shop/ribbons'));
        this.nodeData = this.el.dataset;
        if (this.nodeData.filterId !== undefined) {
            this.data = await this.waitFor(rpc(
                '/shop/categories', {'filter_id': parseInt(this.nodeData.filterId)}
            ))
        } else {
            this.data = [];
        }
    }

    start(){
        this.registerCleanup(listenSizeChange(this.render.bind(this)));
        this.render();
    }

    render(){
        const heightToSpan = {
            'small': 2,
            'medium': 2,
            'large': 4,
        }
        const heightToRow = {
            'small': "10vh",
            'medium': "15vh",
            'large': "15vh",
        }

        let alignmentClass = " justify-content-between";
        if (this.nodeData.alignment == "right"){
            alignmentClass += " align_category_right";
        }else if (this.nodeData.alignment == "center"){
            alignmentClass = " align_category_center";
        }

        const category_grid = this.el.querySelector(".s_category_container");
        category_grid.querySelectorAll(".category_item").forEach(el => {el.remove()});
        category_grid.appendChild(renderToFragment(
            "website_sale.dynamic_filter_template_categories",
            {
                data: this.data,
                ribbons: this.ribbons,
                get_ribbon: this.get_ribbon,
                height: heightToSpan[this.nodeData.height],
                alignmentClass: alignmentClass,
                buttonText: _t(this.nodeData.button),
            }
        ));
        const columns = uiUtils.isSmall()? 1 : parseInt(this.nodeData.columns);
        category_grid.style.setProperty(
            "grid-template-columns", `repeat(${columns}, calc((100% / ${columns}) - 0.7rem))`
        );
        category_grid.style.setProperty(
            "grid-auto-rows", `minmax(${heightToRow[this.nodeData.height]}, auto)`
        );

        const allProducts = this.el.querySelector(".all_products");
        if (this.nodeData.allProducts == "true"){
            allProducts.classList.remove("d-none");
            const allProductsOverlay = allProducts.querySelector(".s_category_overlay");
            allProductsOverlay.classList.remove("justify-content-between", "align_category_right", "align_category_center");
            allProductsOverlay.className += alignmentClass;
            const allProductsHeadingEl = allProducts.querySelector(".all_products_heading");
            allProductsHeadingEl.textContent = allProductsHeadingEl
                ? allProductsHeadingEl.textContent.trim()
                : "All Collections";
            allProducts.querySelector("a").textContent = this.nodeData.button;
            if(['large', 'medium'].includes(this.nodeData.height) || this.nodeData.columns == 5){
                allProducts.style.setProperty("grid-column", "span 2")
            }else{
                allProducts.style.setProperty("grid-column", "span 1")
            }
        }else{
            allProducts.classList.add("d-none");
        }
    }

    get_ribbon(ribbonId){
        if (ribbonId){
            return this.ribbons.find(ribbon => ribbon.id === parseInt(ribbonId));
        }
        return { name: "", bg_color: "", text_color: "", position: "left", style: "ribbon" };
    }
}

registry
    .category("public.interactions")
    .add("website_sale.dynamic_snippet_category", dynamicCategorySnippet);

registry
    .category("public.interactions.edit")
    .add("website_sale.dynamic_snippet_category", {Interaction: dynamicCategorySnippet});
