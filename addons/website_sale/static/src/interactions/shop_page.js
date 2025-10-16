import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { hasTouch, isBrowserFirefox } from '@web/core/browser/feature_detection';
import { redirect } from '@web/core/utils/urls';

export class ShopPage extends Interaction {
    static selector = '.o_wsale_products_page';
    dynamicContent = {
        'form.js_attributes input, form.js_attributes select': {
            't-on-change.prevent': this.onChangeAttribute,
        },
        '.o_wsale_products_searchbar_form': { 't-on-submit': this.onSearch },
        '.o_wsale_filmstrip_wrapper': {
            't-on-mousedown': this.onMouseDown,
            't-on-mouseleave': this.onMouseLeave,
            't-on-mouseup': this.onMouseUp,
            't-on-mousemove': this.onMouseMove,
            't-on-click': this.onMouseClick,
        },
        '.o_wsale_attribute_search_bar': { 't-on-input': this.searchAttributeValues },
        '.o_wsale_view_more_btn': { 't-on-click': this.onToggleViewMoreLabel },
    };

    setup() {
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
    }

    start() {
        // This allows conditional styling for the filmstrip.
        const filmstripContainer = this.el.querySelector('#o_wsale_categories_filmstrip');
        const filmstripWrapper = this.el.querySelector('.o_wsale_filmstrip_wrapper');
        const isFilmstripScrollable = filmstripWrapper
            ? filmstripWrapper.scrollWidth > filmstripWrapper.clientWidth
            : false;
        if (isBrowserFirefox() || hasTouch() || !isFilmstripScrollable) {
            filmstripContainer?.classList.add('o_wsale_filmstrip_fancy_disabled');
        }
    }

    /**
     * Update the URL search params based on the selected attribute values and tags.
     *
     * @param {Event} ev
     */
    onChangeAttribute(ev) {
        const productGrid = this.el.querySelector('.o_wsale_products_grid_table_wrapper');
        if (productGrid) {
            productGrid.classList.add('opacity-50');
        }
        const form = ev.currentTarget.closest('form');
        const filters = form.querySelectorAll('input:checked, select');
        const attributeValues = new Map();
        const tags = new Set();
        for (const filter of filters) {
            if (filter.value) {
                if (filter.name === 'attribute_value') {
                    // Group attribute value ids by attribute id.
                    const [attributeId, attributeValueId] = filter.value.split('-');
                    const valueIds = attributeValues.get(attributeId) ?? new Set();
                    valueIds.add(attributeValueId);
                    attributeValues.set(attributeId, valueIds);
                } else if (filter.name === 'tags') {
                    tags.add(filter.value);
                }
            }
        }
        const url = new URL(form.action);
        const searchParams = url.searchParams;
        // Aggregate all attribute values belonging to the same attribute into a single
        // `attribute_values` search param.
        for (const entry of attributeValues.entries()) {
            searchParams.append('attribute_values', `${entry[0]}-${[...entry[1]].join(',')}`);
        }
        // Aggregate all tags into a single `tags` search param.
        if (tags.size) {
            searchParams.set('tags', [...tags].join(','));
        }
        redirect(`${url.pathname}?${searchParams.toString()}`);
    }

    /**
     * Update the URL search params based on the search query.
     *
     * @param {Event} ev
     */
    onSearch(ev) {
        if (!this.el.querySelector('.dropdown_sorty_by')) return;
        const form = ev.currentTarget;
        if (!ev.defaultPrevented && !form.matches('.disabled')) {
            ev.preventDefault();
            const url = new URL(form.action);
            const searchParams = url.searchParams;
            if (form.querySelector('[name=noFuzzy]')?.value === 'true') {
                searchParams.set('noFuzzy', 'true');
            }
            const input = form.querySelector('input.search-query');
            searchParams.set(input.name, input.value);
            redirect(`${url.pathname}?${searchParams.toString()}`);
        }
    }

    onMouseDown(ev) {
        this.filmStripIsDown = true;
        this.filmStripStartX = ev.pageX - ev.currentTarget.offsetLeft;
        this.filmStripScrollLeft = ev.currentTarget.scrollLeft;
        this.filmStripMoved = false;
    }

    onMouseLeave(ev) {
        if (!this.filmStripIsDown) {
            return;
        }
        ev.currentTarget.classList.remove('activeDrag');
        this.filmStripIsDown = false
    }

    onMouseUp(ev) {
        this.filmStripIsDown = false;
        ev.currentTarget.classList.remove('activeDrag');
    }

    onMouseMove(ev) {
        if (!this.filmStripIsDown) return;
        ev.preventDefault();
        ev.currentTarget.classList.add('activeDrag');
        this.filmStripMoved = true;
        const x = ev.pageX - ev.currentTarget.offsetLeft;
        const walk = (x - this.filmStripStartX) * 2;
        ev.currentTarget.scrollLeft = this.filmStripScrollLeft - walk;
    }

    onMouseClick(ev) {
        if (this.filmStripMoved) {
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    /**
     * Search attribute values based on the input text.
     *
     * @param {Event} ev
     */
    searchAttributeValues(ev) {
        const input = ev.target;
        const searchValue = input.value.toLowerCase();

        document.querySelectorAll(`#${input.dataset.containerId} .form-check`).forEach(item => {
            const labelText = item.querySelector('.form-check-label').textContent.toLowerCase();
            item.style.display = labelText.includes(searchValue) ? '' : 'none'
        });
    }

    /**
     * Toggle the button text between "View More" and "View Less".
     *
     * @param {MouseEvent} ev
     */
    onToggleViewMoreLabel(ev) {
        const button = ev.target;
        const isExpanded = button.getAttribute('aria-expanded') === 'true';

        button.innerHTML = isExpanded ? "View Less" : "View More";
    }
}

registry.category('public.interactions').add('website_sale.shop_page', ShopPage);
