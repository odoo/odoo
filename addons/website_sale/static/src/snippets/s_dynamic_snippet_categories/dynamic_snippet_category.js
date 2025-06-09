import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { utils as uiUtils } from '@web/core/ui/ui_service';
import { renderToFragment } from '@web/core/utils/render';
import { Interaction } from '@web/public/interaction';
import { session } from '@web/session';


const SIZE_CONFIG = {
    small: { span: 2, row: '10vh' },
    medium: { span: 2, row: '15vh' },
    large: { span: 4, row: '15vh' },
};
const  ALIGNMENT_CLASSES_MAPPING = {
    left: ['justify-content-between'],
    center: ['align_category_center'],
    right: ['justify-content-between', 'align_category_right'],
};
const CATEGORY_TEMPLATE = {
    default: 'website_sale.dynamic_filter_template_categories',
    clickable: 'website_sale.dynamic_filter_template_categories_clickable_items',
}
const  ALIGNMENT_CLASSES = [
    'justify-content-between', 'align_category_right', 'align_category_center',
];
const BUTTON_CLASSES = ['oe_unremovable', 'stretched-link', 'opacity-0', 'p-0', 'h-0'];

export class dynamicSnippetCategory extends Interaction {
    static selector = '.s_dynamic_category';
    dynamicContent = {
        _window: { "t-on-resize": this.throttled(this.render) },
    };

    async willStart() {
        if(!session.has_ecommerce_access){
            this.el.querySelector('.all_products').classList.add('d-none');
            this.data = [];
            return;
        }
        const categoryId = this.el.dataset.categoryId;
        this.data = categoryId != ''
            ? await this.waitFor(rpc('/shop/get_categories', { category_id: parseInt(categoryId) }))
            : await this.waitFor(rpc('/shop/get_categories'));
    }

    start() {
        this.render();
    }

    destroy() {
        const categoryWrapperEl = this.el.querySelector('.s_dynamic_category_wrapper');
        categoryWrapperEl.replaceChildren();
        this.el.querySelector('.all_products').classList.add('d-none');
    }

    render() {
        const nodeData = this.el.dataset;

        // Setup mappings
        const alignmentClass =  ALIGNMENT_CLASSES_MAPPING[nodeData.alignment];
        const categoryGrid = this.el.querySelector('.s_category_container');
        const categoryWrapperEl = this.el.querySelector('.s_dynamic_category_wrapper');
        const sizeConfig = SIZE_CONFIG[nodeData.size]

        // Clear existing categories and render with new values
        const categoryTemplate = nodeData.isClickable
            ? CATEGORY_TEMPLATE.clickable
            : CATEGORY_TEMPLATE.default;
        categoryWrapperEl.replaceChildren(renderToFragment(categoryTemplate, {
            data: this.data,
            size: sizeConfig.span,
            alignmentClass: alignmentClass.join(' '),
            buttonText: _t(nodeData.button),
        }))
        // Apply styling to category grid layout
        const columns = uiUtils.isSmall() ? 1 : parseInt(nodeData.columns);
        categoryGrid.style.setProperty('--DynamicCategory-columns', `${columns}`);
        categoryGrid.style.setProperty(
            'grid-auto-rows', `minmax(${sizeConfig.row}, auto)`,
        );

        // Setup 'All Products' item visibility and styling
        this.adaptAllProductsItem(nodeData, columns, alignmentClass);
    }

    adaptAllProductsItem(nodeData, columns, alignmentClass){
        const allProductsItem = this.el.querySelector('.all_products');
        if (nodeData.allProductsItem === 'true' && session.has_ecommerce_access) {
            allProductsItem.classList.remove('d-none');

            // Update 'All Products' item overlay alignment
            const overlay = allProductsItem.querySelector('.s_category_overlay');
            overlay.classList.remove(... ALIGNMENT_CLASSES);
            overlay.classList.add(...alignmentClass);

            // Set heading and button text for 'All Products' item
            allProductsItem.querySelector('a').textContent = nodeData.button;

            // Adjust 'All Product' number of columns
            const shouldSpanTwo = columns !== 1 &&
                (['large', 'medium'].includes(nodeData.size) || columns === 5);
            allProductsItem.style.setProperty('grid-column', `span ${shouldSpanTwo ? 2 : 1}`);

            // Toggle related elements and styles for interactivity
            const allProductsButtonEl = allProductsItem.querySelector('.s_dynamic_category_button');
            const allProductsArrowEl = allProductsItem.querySelector('.s_dynamic_category_arrow');
            const allProductsImgEl = allProductsItem.querySelector('.s_category_image');
            const allProductsFilterEl = allProductsItem.querySelector('.s_category_filter');
            const allProductsOverlayEl = allProductsItem.querySelector('.s_category_overlay');
            const allProductsTitleEl = allProductsItem.querySelector('h3');

            const isClickable = Boolean(nodeData.isClickable);
            this.toggleClass(allProductsItem, 'opacity-trigger-hover', isClickable);
            BUTTON_CLASSES.forEach(
                className => this.toggleClass(allProductsButtonEl, className, isClickable)
            );
            this.toggleClass(allProductsArrowEl, 'd-none', !isClickable);
            this.toggleClass(allProductsImgEl, 'transition-base', isClickable);
            this.toggleClass(allProductsFilterEl, 'd-none', !isClickable);
            this.toggleClass(allProductsOverlayEl, 'z-0', isClickable);
            this.toggleClass(allProductsTitleEl, 'mb-0', isClickable);
        } else {
            allProductsItem.classList.add('d-none');
        }
    }

    toggleClass(el, className, condition){
        el.classList.toggle(className, condition);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.dynamic_snippet_category', dynamicSnippetCategory);

registry
    .category('public.interactions.edit')
    .add('website_sale.dynamic_snippet_category', {Interaction: dynamicSnippetCategory});
