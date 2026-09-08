import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
import { _t } from '@web/core/l10n/translation';
import { createFilterDropdown, fetchProductSearchData, renderAttributeFilter } from './product_search_utils';

export class ProductSearchSnippet extends Interaction {
    static selector = '.s_product_search';
    dynamicContent = {
        '.s_product_search_btn': { 't-on-click': this.onClickSearch },
        '.s_product_search_input, .s_product_search_min_price, .s_product_search_max_price': {
            't-on-keydown': this.onKeydown,
        },
        '.s_product_search_filters': { 't-on-change': this.onChangeFilter },
    };

    async willStart() {
        const { tags, attributes } = await this.waitFor(fetchProductSearchData());
        this.tags = tags;
        this.attributes = attributes;
    }

    start() {
        const tagsEl = this.el.querySelector('.s_product_search_tags');
        tagsEl.replaceChildren();
        if (this.tags.length) {
            tagsEl.appendChild(createFilterDropdown('tags', _t('Tags'), this.tags));
        }

        const attributesEl = this.el.querySelector('.s_product_search_attributes');
        for (const filterEl of attributesEl.querySelectorAll('.s_product_search_attribute_filter')) {
            renderAttributeFilter(filterEl, this.attributes);
        }
    }

    onKeydown(ev) {
        if (ev.key === 'Enter') {
            this.onClickSearch();
        }
    }

    onChangeFilter(ev) {
        const groupEl = ev.target.closest('.s_product_search_filter_group');
        if (!groupEl) {
            return;
        }
        const btnEl = groupEl.querySelector('.s_product_search_filter_btn');
        const labelEl = btnEl.querySelector('.flex-shrink-0');
        const selectedEl = groupEl.querySelector('.s_product_search_filter_selected');
        const checkedNames = [...groupEl.querySelectorAll('.s_product_search_filter_checkbox:checked')]
            .map((checkboxEl) => checkboxEl.closest('.form-check').querySelector('.form-check-label').textContent);
        selectedEl.textContent = checkedNames.join(', ');
        const gap = parseFloat(getComputedStyle(btnEl).columnGap) || 0;
        const availableWidth = btnEl.clientWidth - labelEl.getBoundingClientRect().width - gap;
        const overflowMarginRatio = 0.3;
        if (selectedEl.scrollWidth > availableWidth * (1 - overflowMarginRatio)) {
            selectedEl.textContent = _t('%s selected', checkedNames.length);
        }
    }

    getCheckedValues(groupEl) {
        return [...groupEl.querySelectorAll('.s_product_search_filter_checkbox:checked')]
            .map((checkboxEl) => checkboxEl.value);
    }

    onClickSearch() {
        redirect(`/shop?${this.getSearchParams().toString()}`);
    }

    /**
     * @returns {URLSearchParams} the query params to redirect to /shop with, based on the
     *  current filter values.
     */
    getSearchParams() {
        const searchParams = new URLSearchParams();
        const search = this.el.querySelector('.s_product_search_input').value.trim();
        const minPrice = this.el.querySelector('.s_product_search_min_price').value;
        const maxPrice = this.el.querySelector('.s_product_search_max_price').value;
        if (search) {
            searchParams.append('search', search);
        }
        if (minPrice) {
            searchParams.append('min_price', minPrice);
        }
        if (maxPrice) {
            searchParams.append('max_price', maxPrice);
        }
        const categoryId = this.el.dataset.categoryId;
        if (categoryId) {
            searchParams.append('category', categoryId);
        }
        const ribbonId = this.el.dataset.ribbonId;
        if (ribbonId) {
            searchParams.append('ribbon', ribbonId);
        }

        const tagIds = new Set();
        const fixedTagId = this.el.dataset.tagId;
        if (fixedTagId) {
            tagIds.add(fixedTagId);
        }
        const tagsGroupEl = this.el.querySelector('.s_product_search_filter_group[data-filter-key="tags"]');
        if (tagsGroupEl) {
            for (const tagId of this.getCheckedValues(tagsGroupEl)) {
                tagIds.add(tagId);
            }
        }
        if (tagIds.size) {
            searchParams.append('tags', [...tagIds].join(','));
        }
        for (const filterEl of this.el.querySelectorAll('.s_product_search_attribute_filter[data-attribute-id]')) {
            const groupEl = filterEl.querySelector('.s_product_search_filter_group');
            if (!groupEl) {
                continue;
            }
            const valueIds = this.getCheckedValues(groupEl);
            if (valueIds.length) {
                searchParams.append(filterEl.dataset.attributeId, valueIds.join(','));
            }
        }

        return searchParams;
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_search_snippet', ProductSearchSnippet);
