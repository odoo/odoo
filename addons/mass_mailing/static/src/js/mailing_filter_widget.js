/** @odoo-module alias=mass_mailing.MailingFilterWidget **/

import { Many2OneField } from '@web/views/fields/many2one/many2one_field';
import core from 'web.core';
import Domain from 'web.Domain';
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

const { Component, useEffect, useRef, useChildSubEnv } = owl;
const _t = core._t;

class CreateFavoriteFilter extends Component {
    setup() {
        this.orm = useService('orm');
        this.saveButtonRef = useRef('saveButton');
        this.inputRef = useRef('input');
        useAutofocus({ refName: 'input', preventScroll: true });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Focus the 'Save' button on 'Tab' key, or directly save the filter on 'Enter'
     *
     * @param {event} ev
     */
    onInputKeydown(ev) {
        if (ev.key === 'Tab') {
            this.saveButtonRef.el.focus();
        } else if (ev.key === 'Enter') {
            this.saveButtonRef.el.dispatchEvent(new Event('click'));
        }
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
    async onSave(ev) {
        const filterName = this.inputRef.el.value.trim();
        if (filterName.length === 0) {
            this.displayNotification({ message: _t("Please provide a name for the filter"), type: 'danger' });
            // Keep the drop-down open, and re-focus the input
            ev.stopPropagation();
            this.inputRef.el.focus();
        } else {
            const newFilterId = await this.orm.create('mailing.filter', [{
                name: filterName,
                mailing_domain: this.env.record.data[this.env.domainField],
                mailing_model_id: this.env.record.data[this.env.modelField][0],
            }]);
            this.env.update([newFilterId, filterName]);
        }
    }
}
CreateFavoriteFilter.template = 'mass_mailing.CreateFavoriteFilter';
CreateFavoriteFilter.defaultProps = { value: '' };

/**
 * Widget to create / remove favorite filters on mass mailing and/or marketing
 * automation, extended from Many2OneField. This widget is designed specifically
 * for 'mailing_filter_id' field on 'mailing.mailing' and 'marketing.campaign'
 * form view.
 *
 * In edit mode, it will allow to save the latest configured domain in form of
 * the favorite filter, or to remove the store filters.
 *
 * @class
 */
export class FieldMailingFilter extends Many2OneField {
    /**
     * This widget is used for 'mass.mailing' and 'marketing.campaign', but
     * the field names that stores domain and recipient models are different
     * for both. So it is strongly recommended to pass them explicitly as props.
     *
     * @override
     */
    setup() {
        super.setup();
        useChildSubEnv({
            update: this.props.update,
            record: this.props.record,
            domainField: this.props.domainField,
            modelField: this.props.modelField,
        });
        this.orm = useService('orm');
        this.resetOnAnyFieldChange = true;
        useEffect(() => {
            // Can't be done in the template because it's in a child component.
            this.autocompleteContainerRef.el.classList.toggle('d-none', !this.filterCount);
        }, () => [this.autocompleteContainerRef, this.filterCount]);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get canSaveFilter() {
        return !this.props.record.data.mailing_filter_id
            || !this.props.value.length
            || this.state.isFloating
            || this.filterDomain !== this.recordDomain;
    }
    get filterCount() {
        return this.props.record.data.mailing_filter_count;
    }
    // By default, domains in recordData are in string format, but
    // adding/removing a leaf from domain widget converts value into object,
    // so we use 'Domain' class to convert them in same (string) format,
    // allowing proper comparison.
    get filterDomain() {
        return new Domain(this.props.record.data.mailing_filter_domain || []).toString();;
    }
    get recordDomain() {
        return new Domain(this.props.record.data[this.props.domainField] || []).toString();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Deletes the saved filter without resetting the current domain.
     *
     * @param {event} ev
     */
    async onFavoriteFilterRemoveClick(ev) {
        const filterId = this.props.record.data.mailing_filter_id[0];
        const mailingDomain = this.props.record.data[this.props.domainField];
        ev.target.disabled = true; // Prevent multiple clicks.
        await this.orm.unlink('mailing.filter', [filterId]);
        this.props.update([]);
        // Preserve the current domain after it was removed from the favorites.
        this.props.record.update({ [this.props.domainField]: mailingDomain });
    }
}

FieldMailingFilter.template = 'mass_mailing.FieldMailingFilter';
FieldMailingFilter.components = {
    ...Many2OneField.components,
    Dropdown,
    DropdownItem,
    CreateFavoriteFilter,
};
FieldMailingFilter.props = {
    ...Many2OneField.props,
    domainField: { type: String, optional: true },
    modelField: { type: String, optional: true },
};
FieldMailingFilter.extractProps = ({ attrs, field }) => {
    return {
        ...Many2OneField.extractProps({ attrs, field }),
        domainField: attrs.options.domain_field || 'mailing_domain',
        modelField: attrs.options.model_field || 'mailing_model_id',
    }
}
registry.category("fields").add("mailing_filter", FieldMailingFilter);
