/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from '@web/core/domain';
import { registry } from '@web/core/registry';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';
import { useState, useEffect } from "@odoo/owl";

export class MailingFilterDropdown extends Dropdown {
    setup() {
        super.setup();
        useEffect((inputFilterEl) => {
            if (inputFilterEl) {
                inputFilterEl.focus();
            }
        }, () => [document.querySelector('.o_mass_mailing_filter_name')]);
    }
}

/**
 * Widget to create / remove favorite filters on mass mailing and/or marketing automation, extended
 * from Many2OneField. This widget is designed specifically for 'mailing_filter_id'
 * field on 'mailing.mailing' and 'marketing.campaign' form view.
 *
 * In edit mode, it will allow to save the latest configured domain
 * in form of the favorite filter, or to remove the store filters.
 *
 */
export class FieldMany2OneMailingFilter extends Many2OneField {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.filter = useState({
            canSaveFilter: false,
        });
        useEffect(() => this._updateFilterIcons());
    }

    /**
     * Updates the 'Add to favorite' / 'Remove' icons' visibility based on the
     * current state, and shows the custom message when no filter is available
     * for the selected model.
     *
     * The filter can be saved if one of those conditions is matched:
     * - No favorite filter is currently set
     * - User emptied the input
     * - User changed the domain when favorite filter is set
     * - The input is currently being edited, known by the "this.state.isFloating" variable
     *
     * @private
     */
    _updateFilterIcons() {
        const el = document.querySelector('.o_mass_mailing_filter_container');
        if (!el || this.props.readonly) {
            return;
        }
        const filterCount = this.props.record.data.mailing_filter_count;
        const dropdown = document.querySelector('.o_field_mailing_filter > .o_field_many2one_selection > .o_input_dropdown')
        if (dropdown) {
            dropdown.classList.toggle('d-none', !filterCount);
        }
        // By default, domains in recordData are in string format, but adding / removing a leaf from domain widget converts
        // value into object, so we use 'Domain' class to convert them in same (string) format, allowing proper comparison.
        let recordDomain;
        let filterDomain;
        try {
            recordDomain = new Domain(this.props.record.data[this.props.domain_field] || []).toString();
            filterDomain = new Domain(this.props.record.data.mailing_filter_domain || []).toString();
        } catch {
            // Don't raise a traceback if a domain set manually doesn't match the format expected.
            // This can happen when we unfocus the domain editor
            this.filter.canSaveFilter = false;
            this.filter.canRemoveFilter = false;
            return;
        }

        const modelFieldElement = this.props.model_field && document.querySelector(
            `input#${this.props.model_field},div [name="${this.props.model_field}"]`);

        let value = "";
        if (modelFieldElement && modelFieldElement.tagName === "span") {
            value = modelFieldElement.textContent;
        } else if (modelFieldElement && modelFieldElement.tagName === "input") {
            value = modelFieldElement.value;
        }

        el.classList.toggle('d-none', recordDomain === '[]');
        this.filter.canSaveFilter = !this.props.record.data.mailing_filter_id
            || value.length
            || this.state.isFloating
            || filterDomain !== recordDomain;
        this.filter.canRemoveFilter = !this.filter.canSaveFilter
    }

    // HANDLERS

    /**
     * Focus the 'Save' button on 'Tab' key, or directly save the filter on 'Enter'
     *
     * @param {event} ev
     */
    onFilterNameInputKeydown(ev) {
        const btnSave = document.querySelector('.o_mass_mailing_btn_save_filter');
        if (ev.key === 'Tab') {
            ev.preventDefault();
            btnSave.focus();
        } else if (ev.key === 'Enter') {
            btnSave.click();
        }
    }

    /**
     * Deletes the saved filter, but we do not reset the applied domain
     * in this case.
     *
     * @param {event} ev
     */
    async onRemoveFilter(ev) {
        const filterId = this.props.record.data.mailing_filter_id[0];
        const mailingDomain = this.props.record.data[this.props.domain_field];
        // Prevent multiple clicks to avoid trying to deleting same record multiple times.
        ev.target.disabled = true;

        await this.orm.unlink('mailing.filter', [filterId]);
        this.update(false);
        this.props.record.update({[this.props.domain_field]: mailingDomain});
    }

    /**
     * Creates a new favorite filter, with the name provided from drop-down and
     * with the 'up to date' domain. If the input is blank, displays the warning
     * and keeps the popup open by preventing event propagation.
     *
     * Note: We do not disable the save button here to avoid multiple clicks as for the delete,
     * because as soon as the 'Save' button is clicked, the popup will be closed immediately.
     *
     * @param {event} ev
     */
    async onSaveFilter(ev) {
        const filterInput = document.querySelector('input.o_mass_mailing_filter_name');
        const filterName = filterInput.value.trim();
        if (filterName.length === 0) {
            this.notification.add(
                _t("Please provide a name for the filter"),
                {type: 'danger'}
            );
            // Keep the drop-down open, and re-focus the input
            ev.stopPropagation();
            filterInput.focus();
        } else {
            const [newFilterId] = await this.env.model.orm.create("mailing.filter", [{
                name: filterName,
                mailing_domain: this.props.record.data[this.props.domain_field],
                mailing_model_id: this.props.record.data[this.props.model_field][0],
            }]);
            this.update([{ id: newFilterId, name: filterName }]);
        }
    }
}
FieldMany2OneMailingFilter.template = 'mass_mailing.MailingFilter';
FieldMany2OneMailingFilter.components = {
    ...Many2OneField.components,
    MailingFilterDropdown,
};
FieldMany2OneMailingFilter.props = {
    ...Many2OneField.props,
    domain_field: { type: String, optional: true },
    model_field: { type: String, optional: true },
};
FieldMany2OneMailingFilter.defaultProps = {
    ...Many2OneField.defaultProps,
    domain_field: "mailing_domain",
    model_field: "mailing_model_id",
};

export const fieldMany2OneMailingFilter = {
    ...many2OneField,
    component: FieldMany2OneMailingFilter,
    supportedOptions: [
        ...many2OneField.supportedOptions,
        {
            label: _t("Domain field"),
            name: "domain_field",
            type: "field",
            supportedTypes: ["char"]
        },
        {
            label: _t("Model field"),
            name: "model_field",
            type: "field",
            supportedTypes: ["char"]
        }
    ],
    extractProps({ options }) {
        const props = many2OneField.extractProps(...arguments);
        props.domain_field = options.domain_field;
        props.model_field = options.model_field;
        return props;
    },
};

registry.category("fields").add("mailing_filter", fieldMany2OneMailingFilter);
