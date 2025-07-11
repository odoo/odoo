import { markup } from "@odoo/owl";
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { utils as uiUtils } from '@web/core/ui/ui_service';
import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";


const SIZE_CONFIG = {
    small: { span: 2, row: '10vh' },
    medium: { span: 2, row: '15vh' },
    large: { span: 4, row: '15vh' },
};
const  ALIGNMENT_CLASSES_MAPPING = {
    left: 'justify-content-between',
    center: 'align_category_center',
    right: 'justify-content-between align_category_right'
};
export const CATEGORY_TEMPLATE = {
    default: 'website_sale.dynamic_filter_template_product_public_category_default',
    clickable: 'website_sale.dynamic_filter_template_product_public_category_clickable_items',
};
const GAP = ['gap-0','gap-1','gap-2','gap-3','gap-4','gap-5'];

export class dynamicSnippetCategory extends DynamicSnippet {
    static selector = '.s_dynamic_snippet_category';

    setup(){
        super.setup();
        this.templateKey = 'website_sale.s_dynamic_snippet_category.grid';
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
        const templateKey = nodeData.isClickable
            ? CATEGORY_TEMPLATE.clickable
            : CATEGORY_TEMPLATE.default;
        const filterFragments = await this.waitFor(rpc(
            '/shop/get_categories',
            Object.assign({
                'category_id': parseInt(nodeData.filterId),
                'template_key': templateKey,
            },
                this.getRpcParameters(),
            )
        ));
        this.data = filterFragments.map(markup);
    }

    getRpcParameters(){
        const res = super.getRpcParameters();
        const nodeData = this.el.dataset;
        const sizeConfig = SIZE_CONFIG[nodeData.size]
        const alignmentClass =  ALIGNMENT_CLASSES_MAPPING[nodeData.alignment];
        const columns = uiUtils.isSmall() ? 1 : parseInt(nodeData.columns)
        const shouldParentSpanTwo = columns !== 1 &&
            (['large', 'medium'].includes(nodeData.size) || columns === 5);

        Object.assign(res, {
            size: sizeConfig.span,
            alignmentClass: alignmentClass,
            buttonText: _t(nodeData.button),
            row: sizeConfig.row,
            show_parent: nodeData.filterId && nodeData.showParent,
            should_parent_span_two: shouldParentSpanTwo,
        });
        return res;
    }

    async render() {
        await super.render();
        const nodeData = this.el.dataset;
        const categoryGrid = this.el.querySelector('.s_category_container');

        // Apply styling to front end components (e.g. grid)
        categoryGrid.style.setProperty(
            '--DynamicCategory-columns',
            `${uiUtils.isSmall() ? 1 : parseInt(this.el.dataset.columns)}`
        );
        categoryGrid.style.setProperty(
            'grid-auto-rows', `minmax(${SIZE_CONFIG[nodeData.size].row}, auto)`,
        );
        categoryGrid.classList.add(GAP[parseInt(nodeData.gap)]);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.dynamic_snippet_category', dynamicSnippetCategory);

registry
    .category('public.interactions.edit')
    .add('website_sale.dynamic_snippet_category', {Interaction: dynamicSnippetCategory});
