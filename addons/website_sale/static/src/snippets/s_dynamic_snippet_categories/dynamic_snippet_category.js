import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { utils as uiUtils } from '@web/core/ui/ui_service';
import { DynamicSnippet } from '@website/snippets/s_dynamic_snippet/dynamic_snippet';


const SIZE_CONFIG = {
    small: { span: 2, row: '10vh' },
    medium: { span: 2, row: '15vh' },
    large: { span: 4, row: '15vh' },
};
const ALIGNMENT_CLASSES_MAPPING = {
    left: 'justify-content-between',
    center: 'align_category_center',
    right: 'justify-content-between align_category_right',
};

export class DynamicSnippetCategory extends DynamicSnippet {
    static selector = '.s_dynamic_snippet_category';

    setup(){
        super.setup();
        this.templateKey = 'website_sale.s_dynamic_snippet_category.grid';
        const nodeData = this.el.dataset;
        nodeData.button = nodeData.button || _t("Explore Now");
        const colsCount = uiUtils.isSmall() ? 1 : parseInt(nodeData.columns);
        const colSpanTwo = colsCount !== 1 && (nodeData.size !== 'small' || colsCount === 5);
        // Pass custom data to the template.
        nodeData.customTemplateData = JSON.stringify({
            size: SIZE_CONFIG[nodeData.size]?.span,
            alignmentClass: ALIGNMENT_CLASSES_MAPPING[nodeData.alignment],
            buttonText: nodeData.button,
            colSpanTwo: colSpanTwo,
            includeParent: nodeData.parentCategoryId && nodeData.showParent,
            parentCategoryId: parseInt(nodeData.parentCategoryId),
        });
    }

    getQWebRenderOptions() {
        const nodeData = this.el.dataset;
        return Object.assign(super.getQWebRenderOptions(...arguments), {
            colsCount: uiUtils.isSmall() ? 1 : parseInt(nodeData.columns),
            rowSize: SIZE_CONFIG[nodeData.size].row,
            gap: nodeData.gap,
            rounded: nodeData.rounded,
        });
    }

    getRpcParameters(){
        return Object.assign(super.getRpcParameters(), {
            parentId: parseInt(this.el.dataset.parentCategoryId),
        });
    }

}

registry
    .category('public.interactions')
    .add('website_sale.dynamic_snippet_category', DynamicSnippetCategory);

registry
    .category('public.interactions.edit')
    .add('website_sale.dynamic_snippet_category', {Interaction: DynamicSnippetCategory});
