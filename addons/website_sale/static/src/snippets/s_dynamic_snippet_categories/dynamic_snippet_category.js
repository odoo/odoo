import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { DynamicSnippet } from '@website/snippets/s_dynamic_snippet/dynamic_snippet';


export class DynamicSnippetCategory extends DynamicSnippet {
    static selector = '.s_dynamic_snippet_category';

    setup(){
        super.setup();
        this.templateKey = 'website_sale.s_dynamic_snippet_category.grid';
        const nodeData = this.el.dataset;
        const buttonText = nodeData.button || _t("Explore Now");
        // Pass custom data to the template.
        nodeData.customTemplateData = JSON.stringify({
            buttonText: buttonText,
            includeParent: nodeData.parentCategoryId && nodeData.showParent,
            parentCategoryId: parseInt(nodeData.parentCategoryId),
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
    .category("public.interactions.preview")
    .add('website_sale.dynamic_snippet_category', {Interaction: DynamicSnippetCategory});
