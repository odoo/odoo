import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
import { _t } from '@web/core/l10n/translation';
import { fetchProductSearchData } from './product_search_utils';

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
        const needTags = !this.el.querySelector('.s_product_search_tags_wrap').classList.contains('d-none');
        const attributeIds = [...this.el.querySelectorAll('.s_product_search_attribute_filter[data-attribute-id]')]
            .map((filterEl) => parseInt(filterEl.dataset.attributeId));
        this.tags = [];
        this.attributes = [];
        if (!needTags && !attributeIds.length) {
            return;
        }
        const { tags = [], attributes = [] } = await this.waitFor(
            fetchProductSearchData({ tags: needTags, attributes: attributeIds })
        );
        this.tags = tags;
        this.attributes = attributes;
    }

    start() {
        const tagsMenuEl = this.el.querySelector('.s_product_search_tags .s_product_search_filter_menu');
        if (this.tags.length && tagsMenuEl) {
            this.renderAt('website_sale.s_product_search.filter_items', { key: 'tags', items: this.tags }, tagsMenuEl);
        } else {
            // Hide the tags field if all the tags were removed
            this.el.classList.add('o_wsale_product_search_no_tags');
            this.registerCleanup(() => this.el.classList.remove('o_wsale_product_search_no_tags'));
        }
        // Only the dropdown toggles are saved in the page, the menu items are rendered here.
        for (const filterEl of this.el.querySelectorAll('.s_product_search_attribute_filter')) {
            const attribute = this.attributes.find((attr) => attr.id === parseInt(filterEl.dataset.attributeId));
            const menuEl = filterEl.querySelector('.s_product_search_filter_menu');
            if (attribute && menuEl) {
                this.renderAt('website_sale.s_product_search.filter_items', {
                    key: `attribute_${attribute.id}`,
                    items: attribute.value_ids,
                    displayType: attribute.display_type,
                }, menuEl);
            } else {
                this.hideUnavailableFilter(filterEl);
            }
        }

        this.registerCleanup(() => {
            for (const selectedEl of this.el.querySelectorAll('.s_product_search_filter_selected')) {
                selectedEl.textContent = '';
            }
        });
    }

    /**
     * Hides the filter of an attribute which is no longer available
     *
     * @param {HTMLElement} filterEl
     */
    hideUnavailableFilter(filterEl) {
        filterEl.classList.add('d-none');
        this.registerCleanup(() => filterEl.classList.remove('d-none'));
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
        const labelEl = btnEl.querySelector('.s_product_search_filter_label');
        const selectedEl = groupEl.querySelector('.s_product_search_filter_selected');
        const checkedNames = [...groupEl.querySelectorAll(
            '.form-check:has(.s_product_search_filter_checkbox:checked) .form-check-label'
        )].map((checkedLabelEl) => checkedLabelEl.textContent);
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
            const valueIds = this.getCheckedValues(filterEl);
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
