/** @odoo-module alias=mass_mailing.MailingFilterWidget **/

import { FieldMany2One } from 'web.relational_fields';
import core from 'web.core';
import Domain from 'web.Domain';
import fieldRegistry from 'web.field_registry';

const _t = core._t;

/**
 * Widget to create / remove favorite filters on mass mailing and/or marketing automation, extended
 * from FieldMany2One. This widget is designed specifically for 'mailing_filter_id'
 * field on 'mailing.mailing' and 'marketing.campaign' form view.
 *
 * In edit mode, it will allow to save the latest configured domain
 * in form of the favorite filter, or to remove the store filters.
 *
 * @class
 */
const FieldMailingFilter = FieldMany2One.extend({
    template: 'mass_mailing.FieldMailingFilter',
    events: Object.assign({}, FieldMany2One.prototype.events, {
        'click .o_mass_mailing_btn_save_filter': '_onFavoriteFilterSaveClick',
        'click .o_mass_mailing_remove_filter': '_onFavoriteFilterRemoveClick',
        'keydown .o_mass_mailing_filter_name': '_onFavoriteFilterNameInputKeydown',
        'shown.bs.dropdown': '_onFavoriteFilterDropdownShown',
    }),
    resetOnAnyFieldChange: true,

    /**
     * This widget is used for 'mass.mailing' and 'marketing.campaign', but
     * the field names that stores domain and recipient models are different
     * for both. So, it is strongly recommended to pass them explicitly with
     * `nodeOptions`.
     *
     * @override
     */
    init() {
        this._super(...arguments);
        this.domainFieldName = this.nodeOptions.domain_field || 'mailing_domain';
        this.modelFieldName = this.nodeOptions.model_field || 'mailing_model_id';
    },

    /**
     * This widget now has two inputs, one for m2o and another for filter
     * name. So this override makes sure that 'this.$input' now refers to
     * only main input instead of both.
     * see FieldMany2One#start for more details.
     *
     * @override
     */
    start() {
        const def = this._super(...arguments);
        this.$input = this.$('input.o_input');
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @override
     * @private
     */
    _renderEdit() {
        this._super(...arguments);
        this._updateFilterIcons();
    },

    /**
     * Updates the 'Add to favorite' / 'Remove' icons' visibility based on the
     * current state, and shows the custom message when no filter is available
     * for the selected model.
     *
     * The filter can be saved if one of those conditions is matched:
     * - No favorite filter is currently set
     * - User emptied the input
     * - User changed the domain when favorite filter is set
     * - The input is currently being edited, known by the "this.floating" variable
     *   (see FieldMany2One#start for more information about the floating variable).
     *
     * @private
     */
    _updateFilterIcons: function () {
        const filterCount = this.recordData.mailing_filter_count;
        this.el.querySelector('.o_mass_mailing_no_filter').classList.toggle('d-none', filterCount);
        this.el.querySelector('.o_field_many2one_selection > .o_input_dropdown').classList.toggle('d-none', !filterCount);
        // By default, domains in recordData are in string format, but adding / removing a leaf from domain widget converts
        // value into object, so we use 'Domain' class to convert them in same (string) format, allowing proper comparison.
        const recordDomain = new Domain(this.recordData[this.domainFieldName] || []).toString();
        const filterDomain = new Domain(this.recordData.mailing_filter_domain || []).toString();
        this.el.querySelector('.o_mass_mailing_filter_container').classList.toggle('d-none', recordDomain === '[]');
        const canSaveFilter = !this.recordData.mailing_filter_id
            || !this.$input.val().length
            || this.floating
            || filterDomain !== recordDomain;
        this.el.querySelector('.o_mass_mailing_save_filter_container').classList.toggle('d-none', !canSaveFilter);
        this.el.querySelector('.o_mass_mailing_remove_filter').classList.toggle('d-none', canSaveFilter);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * On opening the drop-down, remove existing input value (if any) and set
     * focus on input
     *
     * @private
     * @param {event} ev
     */
    _onFavoriteFilterDropdownShown(ev) {
        const filterInput = ev.target.querySelector('input.o_mass_mailing_filter_name');
        filterInput.value = '';
        filterInput.focus({ preventScroll: true });
    },

    /**
     * Focus the 'Save' button on 'Tab' key, or directly save the filter on 'Enter'
     *
     * @private
     * @param {event} ev
     */
    _onFavoriteFilterNameInputKeydown(ev) {
        const btnSave = this.el.querySelector('.o_mass_mailing_btn_save_filter');
        if (ev.key === 'Tab') {
            btnSave.focus();
        } else if (ev.key === 'Enter') {
            btnSave.click();
        }
    },

    /**
     * Prevent opening m2o drop-down on click of filter's input (if drop-down is open)
     *
     * @override
     * @private
     */
    _onInputClick: function () {
        if (!this.el.querySelector('.o_mass_mailing_save_filter_container .dropdown-menu').classList.contains('show')) {
            this._super(...arguments);
        }
    },

    /**
     * Update the filter / filter icons visibility with respect to current state
     *
     * @override
     * @private
     * @param {event} ev
     */
    _onInputKeyup(ev) {
        this._super(...arguments);
        this._updateFilterIcons();
    },

    /**
     * Deletes the saved filter, but we do not reset the applied domain
     * in this case.
     *
     * @private
     * @param {event} ev
     */
    async _onFavoriteFilterRemoveClick(ev) {
        const filterId = this.recordData.mailing_filter_id.res_id;
        const mailingDomain = this.recordData[this.domainFieldName];
        // Prevent multiple clicks to avoid trying to deleting same record multiple times.
        ev.target.disabled = true;
        // Avoid calling any 'onchange' (that depends on filter and might reset the domain) immediately
        // after filter is removed. It shouldn't have any side effects because we don't want to change
        // anything in any case when filter is unliked with with this widget.
        this._setValue(false, {notifyChange: false});
        await this._rpc({
            model: 'mailing.filter',
            method: 'unlink',
            args: [filterId],
        });
        // When a filter is removed, compute method on mass mailing resets the domain while saving the
        // record. This hack re-applies the domain and thus we don't loose it when record is saved.
        this.trigger_up('field_changed', {
            dataPointID: this.record.id,
            changes: {
                [this.domainFieldName]: mailingDomain,
            },
        });
    },

    /**
     * Creates a new favorite filter, with the name provided from drop-down and
     * with the 'up to date' domain. If the input is blank, displays the warning
     * and keeps the popup open by preventing event propagation.
     *
     * Note: We do not disable the save button here to avoid multiple clicks as for the delete,
     * because as soon as the 'Save' button is clicked, the popup will be closed immediately.
     *
     * @private
     * @param {event} ev
     */
    async _onFavoriteFilterSaveClick(ev) {
        const filterInput = this.el.querySelector('input.o_mass_mailing_filter_name');
        const filterName = filterInput.value.trim();
        if (filterName.length === 0) {
            this.displayNotification({ message: _t("Please provide a name for the filter"), type: 'danger' });
            // Keep the drop-down open, and re-focus the input
            ev.stopPropagation();
            filterInput.focus();
        } else {
            const newFilterId = await this._rpc({
                model: 'mailing.filter',
                method: 'create',
                args: [{
                    name: filterName,
                    mailing_domain: this.recordData[this.domainFieldName],
                    mailing_model_id: this.recordData[this.modelFieldName].data.id,
                }]
            });
            this._setValue(newFilterId);
        }
    },
});

fieldRegistry.add('mailing_filter', FieldMailingFilter);

export default FieldMailingFilter;
