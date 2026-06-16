import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';
import { _t } from '@web/core/l10n/translation';
import { CustomerAddress } from '@portal/interactions/address';

const IDENTIFIER_PREFIX = 'additional_identifier_';
// Event broadcast by the address interaction (below) whenever the customer changes the
// address country, carrying the identifiers offered for that country.
const COUNTRY_CHANGED_EVENT = 'additional-identifiers-country-changed';

export class AdditionalIdentifiers extends Interaction {
    // /shop/address & /my/address
    static selector = '.o_additional_identifiers_portal';
    dynamicContent = {
        '.o_add_identifier_item': { 't-on-click.prevent': this.onAddIdentifier },
        '.o_remove_identifier': { 't-on-click.prevent': this.onRemoveIdentifier },
        '.o_additional_identifier_field input': { 't-on-change': this.onChangeValue },
        _root: { [`t-on-${COUNTRY_CHANGED_EVENT}`]: this.onCountryChanged },
    };

    setup() {
        this._syncDropdown();
    }

    /**
     * Reveal the identifier input and remove it from the "Add identifier" dropdown.
     *
     * @param {Event} ev
     */
    onAddIdentifier(ev) {
        const key = ev.currentTarget.dataset.identifierKey;
        const field = this._getField(key);
        if (!field) return;
        field.style.display = '';
        this._toggleDropdownItem(key, false);
        this._updateDropdownVisibility();
        field.querySelector('input')?.focus();
    }

    /**
     * Remove an identifier: clear its value, hide its input and offer it back in the dropdown.
     *
     * @param {Event} ev
     */
    onRemoveIdentifier(ev) {
        const field = ev.currentTarget.closest('.o_additional_identifier_field');
        this._removeField(field);
    }

    /**
     * Hide an emptied identifier input again and offer it back in the dropdown.
     *
     * @param {Event} ev
     */
    onChangeValue(ev) {
        if (ev.currentTarget.value.trim() !== '') return;
        this._removeField(ev.currentTarget.closest('.o_additional_identifier_field'));
    }

    /**
     * Rebuild the offered identifiers for the newly selected country, clearing any value the
     * customer had entered. Additional identifiers are country-specific, so they are not carried
     * over when the country changes (the emptied fields drop the previous values on submit).
     *
     * @param {CustomEvent} ev
     */
    onCountryChanged(ev) {
        const metadata = ev.detail.metadata || {};
        this.el.replaceChildren();
        for (const [key, meta] of Object.entries(metadata)) {
            this.el.appendChild(this._buildField(key, meta));
        }
        if (Object.keys(metadata).length) {
            this.el.appendChild(this._buildDropdown(metadata));
        }
        // Rebind the add/remove/change listeners to the freshly built nodes.
        this.updateContent();
        this._syncDropdown();
    }

    _removeField(field) {
        const input = field.querySelector('input');
        if (input) {
            input.value = '';  // cleared inputs are dropped on submit (handles the removal)
        }
        field.style.display = 'none';
        this._toggleDropdownItem(field.dataset.identifierKey, true);
        this._updateDropdownVisibility();
    }

    _getField(key) {
        return this.el.querySelector(`.o_additional_identifier_field[data-identifier-key="${key}"]`);
    }

    _toggleDropdownItem(key, show) {
        const item = this.el.querySelector(`.o_add_identifier_item[data-identifier-key="${key}"]`);
        if (item) {
            item.classList.toggle('d-none', !show);
        }
    }

    _updateDropdownVisibility() {
        // Hide the whole "Add identifier" control once every identifier is shown.
        const dropdown = this.el.querySelector('.o_add_identifier_dropdown');
        if (!dropdown) return;
        const hasAvailable = !!this.el.querySelector('.o_add_identifier_item:not(.d-none)');
        dropdown.classList.toggle('d-none', !hasAvailable);
    }

    /** Hide the dropdown entry of every identifier whose field is already shown (prefilled). */
    _syncDropdown() {
        this.el.querySelectorAll('.o_additional_identifier_field').forEach((field) => {
            if (field.style.display !== 'none') {
                this._toggleDropdownItem(field.dataset.identifierKey, false);
            }
        });
        this._updateDropdownVisibility();
    }

    /** Build an empty, hidden identifier field. Mirrors the QWeb template. */
    _buildField(key, meta) {
        const field = document.createElement('div');
        field.className = 'o_additional_identifier_field mb-2';
        field.dataset.identifierKey = key;
        field.style.display = 'none';

        const label = document.createElement('label');
        label.className = 'col-form-label fw-normal label-optional';
        label.setAttribute('for', `o_additional_identifier_${key}`);
        label.textContent = meta.label || key;

        const group = document.createElement('div');
        group.className = 'input-group';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control';
        input.id = `o_additional_identifier_${key}`;
        input.name = `${IDENTIFIER_PREFIX}${key}`;
        if (meta.placeholder) {
            input.placeholder = meta.placeholder;
        }

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline-secondary o_remove_identifier';
        button.title = _t("Remove");
        button.setAttribute('aria-label', _t("Remove"));
        const icon = document.createElement('i');
        icon.className = 'fa fa-trash-o';
        button.appendChild(icon);

        group.append(input, button);
        field.append(label, group);
        return field;
    }

    /** Build the "Add identifier" dropdown listing every offered identifier. */
    _buildDropdown(metadata) {
        const dropdown = document.createElement('div');
        dropdown.className = 'dropdown o_add_identifier_dropdown';

        const button = document.createElement('button');
        button.className = 'btn btn-link p-0';
        button.type = 'button';
        button.setAttribute('data-bs-toggle', 'dropdown');
        button.setAttribute('aria-expanded', 'false');
        const icon = document.createElement('i');
        icon.className = 'fa fa-plus me-1';
        button.append(icon, document.createTextNode(_t("Add identifier")));

        const menu = document.createElement('div');
        menu.className = 'dropdown-menu';
        for (const [key, meta] of Object.entries(metadata)) {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'dropdown-item o_add_identifier_item';
            item.dataset.identifierKey = key;
            item.textContent = meta.label || key;
            menu.appendChild(item);
        }

        dropdown.append(button, menu);
        return dropdown;
    }
}

registry
    .category('public.interactions')
    .add('account.additional_identifiers', AdditionalIdentifiers);

// Broadcast the country's additional identifiers whenever the address country changes, so the
// AdditionalIdentifiers interaction can refresh the offered fields without a page reload.
patch(CustomerAddress.prototype, {
    async _onChangeCountry(init = false) {
        const data = await super._onChangeCountry(init);
        if (!init) {
            const container = this.el.querySelector('.o_additional_identifiers_portal');
            container?.dispatchEvent(new CustomEvent(COUNTRY_CHANGED_EVENT, {
                detail: { metadata: data?.additional_identifiers_metadata || {} },
            }));
        }
        return data;
    },
});
