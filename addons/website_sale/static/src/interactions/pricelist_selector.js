import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';

const SELECT_COUNTRY = 'div[name="country_dropdown"]';
const SELECT_CURRENCY = 'div[name="currency_dropdown"]';


export class PricelistSelector extends Interaction {
    static selector = 'form[name="pricelist_selector"]';

    dynamicContent = {
        [SELECT_COUNTRY]: {
            't-on-show.bs.dropdown.once': this.fetchSelectablePricelists,
        },
        [`${SELECT_COUNTRY} .dropdown-menu .dropdown-item`]: {
            't-on-click': this.locked(this.onClickCountryItem),
        },
        [SELECT_CURRENCY]: {
            't-on-show.bs.dropdown.once': this.fetchSelectablePricelists,
        },
        [`${SELECT_CURRENCY} .dropdown-menu .dropdown-item`]: {
            't-on-click': this.locked(this.onClickCurrencyItem),
        },
    };

    setup() {
        this.countryDropdown = this.el.querySelector(SELECT_COUNTRY);
        this.currencyDropdown = this.el.querySelector(SELECT_CURRENCY);
        this.countryItemTemplate = this.countryDropdown.querySelector('.dropdown-item-template');
        this.currencyItemTemplate = this.currencyDropdown.querySelector('.dropdown-item-template');
        this.dataset = undefined;
    }

    async fetchSelectablePricelists() {
        this.dataset = await this.waitFor(this.services.http.get('/shop/selectable_pricelists'))
            .catch(() => ({}));
        this.updateDropdownItems();
    }

    get currentCountryId() {
        return parseInt(this.el.querySelector('input[name="country_id"]').value)
    }
    get currentCurrencyId() {
        return parseInt(this.el.querySelector('input[name="currency_id"]').value)
    }

    updateDropdownItems() {
        const countryItems = Object.values(this.dataset.countries ?? {})
            .filter((country) => country.id !== this.currentCountryId)
            .map((country) => this.renderDropdownItem(
                this.countryItemTemplate,
                country.id,
                { selector: '[name="country_name"]', attr: 'textContent', value: country.name },
                { selector: '[name="country_name"]', attr: 'title', value: country.name },
                country.image_url
                    ? { selector: '[name="country_flag"] img', attr: 'src', value: country.image_url }
                    : { selector: '[name="country_flag"]', attr: 'hidden', value: true },
            ));
        this.countryDropdown.querySelector('.dropdown-menu').replaceChildren(...countryItems);

        const currencyItems = Object.values(this.dataset.currencies ?? {})
            .filter((currency) => currency.id !== this.currentCurrencyId)
            .map((currency) => this.renderDropdownItem(
                this.currencyItemTemplate,
                currency.id,
                { selector: '[name="currency_name"]', attr: 'textContent', value: currency.symbol },
                { selector: '[name="currency_name"]', attr: 'title', value: currency.name },
            ));
        this.currencyDropdown.querySelector('.dropdown-menu').replaceChildren(...currencyItems);
    }

    renderDropdownItem(itemTemplate, value, ...replaceCommands) {
        const itemEl = itemTemplate.cloneNode(true).querySelector(".dropdown-item");
        itemEl.setAttribute("value", value);
        for (const command of replaceCommands) {
            itemEl.querySelector(command.selector)[command.attr] = command.value;
        }
        return itemEl;
    }

    async onClickCountryItem(ev) {
        const countryId = ev.currentTarget.value;
        const currencyId = this.dataset.countries[countryId].currency_id;
        const pricelistId = this.dataset.currencies[currencyId]?.pricelist_id
            ?? this.dataset.currencies[this.dataset.default_currency_id].pricelist_id;
        await this.changePricelist({ currencyId, countryId, pricelistId });
    }

    async onClickCurrencyItem(ev) {
        const currencyId = ev.currentTarget.value;
        const pricelistId = this.dataset.currencies[currencyId].pricelist_id;
        await this.changePricelist({ currencyId, pricelistId });
    }

    async changePricelist({ countryId, currencyId, pricelistId }) {
        if (countryId) {
            this.el.querySelector('input[name="country_id"]').value = countryId;
        }
        if (currencyId) {
            this.el.querySelector('input[name="currency_id"]').value = currencyId;
        }

        this.el.action = `/shop/change_pricelist/${pricelistId}`;
        this.el.submit();
    }
}


registry.category('public.interactions').add('website_sale.pricelist_selector', PricelistSelector);
