import { Plugin } from '@html_editor/plugin';
import { withSequence } from '@html_editor/utils/resource';
import { BuilderAction } from '@html_builder/core/builder_action';
import { registry } from '@web/core/registry';
import { DEVICE_VISIBILITY } from '@website/builder/option_sequence';
import {
    setDatasetIfUndefined
} from '@website/builder/plugins/options/dynamic_snippet_option_plugin';
import { DynamicSnippetCategoryOption } from './dynamic_snippet_category_options';

const TEMPLATE_OPTIONS = {
    'clickable': 'website_sale.dynamic_filter_template_product_public_category_clickable_items',
    'default': 'website_sale.dynamic_filter_template_product_public_category_default',
}

const SIZE_CONFIG = {
    small: { span: 2, row: '10vh' },
    medium: { span: 2, row: '15vh' },
    large: { span: 4, row: '15vh' },
};

const modelNameFilter = 'product.public.category';

export class DynamicSnippetCategoryOption2 extends DynamicSnippetCategoryOption {
    static selector = 'section.s_dynamic_snippet_category';
    static defaultProps = {
        modelNameFilter,
    };
    static groups = ['website.group_website_designer'];
}

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';
    static dependencies = ['dynamicSnippetOption'];
    selector = DynamicSnippetCategoryOption2.selector;
    modelNameFilter = modelNameFilter;
    resources = {
        builder_options: [
            withSequence(DEVICE_VISIBILITY, DynamicSnippetCategoryOption2),
        ],
        builder_actions: {
            SetCategoryGridColumn,
            SetCategoryGridGap,
            SetCategoryGridRoundness,
            SetCategoryGridSize,
            ToggleClickableAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            for (const [optionName, value] of [
                ['showParent', true],
                ['size', 'medium'],
                ['alignment', 'center'],
            ]) {
                setDatasetIfUndefined(snippetEl, optionName, value);
            }

            for (const [optionName, value] of [
                ['columns', 4], ['rounded', 2], ['gap', 2], ['size', 'medium']
            ]) {
                setDatasetIfUndefined(
                    snippetEl.querySelector('.dynamic_snippet_template'),
                    optionName,
                    value,
                );
            }

            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl, this.modelNameFilter, [],
            );
        }
    }
}

export class SetCategoryGridColumn extends BuilderAction {
    static id = 'setCategoryGridColumns';
    getValue({ editingElement }) {
        return editingElement.querySelector('.dynamic_snippet_template').dataset.columns;
    }
    apply({ editingElement, value }) {
       editingElement.querySelector('.dynamic_snippet_template').dataset.columns = value;
        editingElement.querySelector('.o_category_container').style.setProperty(
            '--DynamicCategory-columns', value,
        );
    }
}

export class SetCategoryGridGap extends BuilderAction {
    static id = 'setCategoryGridGap';
    getValue({ editingElement }) {
        return editingElement.querySelector('.dynamic_snippet_template').dataset.gap;
    }
    apply({ editingElement, value }) {
        editingElement.querySelector('.dynamic_snippet_template').dataset.gap = value;
        let grid = editingElement.querySelector('.o_category_container');
        grid.classList.forEach(cls => {
            if (/^gap-\d+$/.test(cls)) {
                grid.classList.remove(cls);
            }
        });
        grid.classList.add(`gap-${value}`);
    }
}

export class SetCategoryGridRoundness extends BuilderAction {
    static id = 'setCategoryGridRoundness';
    getValue({ editingElement }) {
        return editingElement.querySelector('.dynamic_snippet_template').dataset.rounded;
    }
    apply({ editingElement, value }) {
        editingElement.querySelector('.dynamic_snippet_template').dataset.rounded = value;
        let grid = editingElement.querySelector('.o_category_container');
        grid.classList.forEach(cls => {
            if (/^rounded-\d+$/.test(cls)) {
                grid.classList.remove(cls);
            }
        });
        grid.classList.add(`rounded-${value}`);

    }
}

export class SetCategoryGridSize extends BuilderAction {
    static id = 'setCategoryGridSize'
    isApplied({ editingElement, value }) {
        return editingElement.querySelector('.dynamic_snippet_template').dataset.size == value;
    }
    apply({ editingElement, value }) {
        editingElement.querySelector('.dynamic_snippet_template').dataset.size = value;
        const parentCategoryId = editingElement.dataset.parentCategoryId
        editingElement.querySelectorAll('.s_dynamic_category_item').forEach((categoryItem) => {
            categoryItem.style.setProperty(
                'grid-row',
                `span ${parentCategoryId === categoryItem.dataset.categoryId?
                    '4' : SIZE_CONFIG[value]?.span
                }`
            )
        })
        editingElement.querySelector('.o_category_container').style.setProperty(
            'grid-auto-rows',
            `minmax(${SIZE_CONFIG[value]?.row}, auto)`
        )
    }
}

export class ToggleClickableAction extends BuilderAction {
    static id = 'toggleClickable';
    apply({ editingElement }) {
        const nodeData = editingElement.dataset;
        nodeData.templateKey = nodeData.templateKey === TEMPLATE_OPTIONS['default']
            ? TEMPLATE_OPTIONS['clickable']
            : TEMPLATE_OPTIONS['default'];
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
