import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';

const SELECT_PRICELIST_COUNTRY = 'select[name="country_id"]';
const SELECT_PRICELIST = 'select[name="pricelist_id"]';


export class PricelistSelector extends Interaction {
    static selector = 'form[name="pricelist_selector_ddd"]';

    dynamicContent = {
        _root: {
            't-on-mouseenter': this.locked(this.fetchSelectablePricelists.bind(this)),
        },
        [SELECT_PRICELIST_COUNTRY]: {
            't-on-change': this.onSelectCountry.bind(this),
        },
        [SELECT_PRICELIST]: {
            't-on-change': () => this.submitSelection(),
        },
    };

    setup() {
        this.countrySelect = this.el.querySelector(SELECT_PRICELIST_COUNTRY);
        this.pricelistSelect = this.el.querySelector(SELECT_PRICELIST);
        this.countryOptionTemplate = this.countrySelect.querySelector('option');
        this.pricelistOptionTemplate = this.pricelistSelect.querySelector('option');

        this.currentCountryId = this.selectedCountryId;
        this.currentPricelistId = this.selectedPricelistId;
        this.dataset = undefined;
        this.submitSelection = this.locked(this.submitSelection.bind(this));
    }

    get selectedCountryId() {
        return parseInt(this.countrySelect.value);
    }

    get selectedPricelistId() {
        return parseInt(this.pricelistSelect.value);
    }

    async fetchSelectablePricelists() {
        if (this.dataset !== undefined) {
            return;
        }

        this.dataset = await this.waitFor(rpc('/shop/selectable_pricelists')).catch(() => {});
        this.updateCountryOptions();
    }

    async onSelectCountry() {
        this.updatePricelistOptions();

        // Change to the first pricelist available for that country.
        this.pricelistSelect.selectedIndex = 0;
        await this.submitSelection();
    }

    updateCountryOptions() {
        const countryOptions = Object.values(this.dataset?.country_ids ?? {})
            .map(country => this.renderOption(
                this.countryOptionTemplate,
                { value: country.id, display: country.name, selected: country.selected },
            ));

        // Save the selected country before replacing the initial <option>
        const selectedCountryId = this.selectedCountryId;
        this.countrySelect.replaceChildren(...countryOptions);
        this.countrySelect.value = selectedCountryId;
    }

    updatePricelistOptions() {
        const countryPricelists = new Set(
            this.dataset?.country_ids?.[`${this.selectedCountryId}`]?.pricelist_ids ?? []
        );
        const pricelistOptions = Object.values(this.dataset?.pricelist_ids ?? {})
            .filter(pricelist => countryPricelists.has(pricelist.id))
            .map(pricelist => this.renderOption(
                this.pricelistOptionTemplate,
                {
                    value: pricelist.id,
                    display: pricelist.currency_id.name,
                    selected: pricelist.selected,
                },
            ));

        this.pricelistSelect.replaceChildren(...pricelistOptions);
    }

    renderOption(optionTemplate, { value, display, selected }) {
        const optionEl = optionTemplate.cloneNode();
        optionEl.setAttribute("value", value);
        optionEl.textContent = display;
        optionEl.toggleAttribute("selected", selected ?? false);
        return optionEl;
    }

    async submitSelection() {
        if (
            this.currentCountryId === this.selectedCountryId
            && this.currentPricelistId === this.selectedPricelistId
        ) {
            return;
        }
        this.el.action = `/shop/change_pricelist/${this.selectedPricelistId}`;
        this.el.submit();
    }
}


registry.category('public.interactions').add('website_sale.pricelist_selector', PricelistSelector);
