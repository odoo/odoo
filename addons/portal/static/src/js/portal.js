/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'change select[name="country_id"]': '_onCountryChange',
        'click .o_portal_profile_pic_edit': '_onEditProfilePicClick',
        'change .o_portal_file_upload': '_onFileUploadChange',
        'click .o_portal_profile_pic_clear': '_onProfilePicClearClick',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.$state = this.$('select[name="state_id"]');
        this.$stateOptions = this.$state.filter(':enabled').find('option:not(:first)');
        this._adaptAddressForm();

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptAddressForm: function () {
        var $country = this.$('select[name="country_id"]');
        var countryID = ($country.val() || 0);
        this.$stateOptions.detach();
        var $displayedState = this.$stateOptions.filter('[data-country_id=' + countryID + ']');
        var nb = $displayedState.appendTo(this.$state).show().length;
        this.$state.parent().toggle(nb >= 1);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCountryChange: function () {
        this._adaptAddressForm();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onEditProfilePicClick: function (ev) {
        ev.preventDefault();
        ev.currentTarget.closest("form").querySelector(".o_portal_file_upload").click();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFileUploadChange: function (ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        const formEl = ev.currentTarget.closest("form");
        var reader = new window.FileReader();
        reader.readAsDataURL(ev.currentTarget.files[0]);
        reader.onload = function (ev) {
            formEl.querySelector(".o_wportal_avatar_img").src = ev.target.result;
        };
        formEl.querySelector("#portal_clear_image")?.remove();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        const formEl = ev.currentTarget.closest("form");
        formEl.querySelector(".o_wportal_avatar_img").src = "/web/static/img/placeholder.png";
        // const inputElement = document.createElement("input");
        // inputElement.setAttribute("name", "clear_image");
        // inputElement.setAttribute("id", "forum_clear_image");
        // inputElement.setAttribute("type", "hidden");
        // formEl.append(inputElement);
    },
});

export const PortalHomeCounters = publicWidget.Widget.extend({
    selector: '.o_portal_my_home',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._updateCounters();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return a list of counters name linked to a line that we want to keep
     * regardless of the number of documents present
     * @private
     * @returns {Array}
     */
    _getCountersAlwaysDisplayed() {
        return [];
    },

    /**
     * @private
     */
    async _updateCounters(elem) {
        const needed = Object.values(this.el.querySelectorAll('[data-placeholder_count]'))
                                .map(documentsCounterEl => documentsCounterEl.dataset['placeholder_count']);
        const numberRpc = Math.min(Math.ceil(needed.length / 5), 3); // max 3 rpc, up to 5 counters by rpc ideally
        const counterByRpc = Math.ceil(needed.length / numberRpc);
        const countersAlwaysDisplayed = this._getCountersAlwaysDisplayed();

        const proms = [...Array(Math.min(numberRpc, needed.length)).keys()].map(async i => {
            const documentsCountersData = await rpc("/my/counters", {
                counters: needed.slice(i * counterByRpc, (i + 1) * counterByRpc)
            });
            Object.keys(documentsCountersData).forEach(counterName => {
                const documentsCounterEl = this.el.querySelector(`[data-placeholder_count='${counterName}']`);
                documentsCounterEl.textContent = documentsCountersData[counterName];
                // The element is hidden by default, only show it if its counter is > 0 or if it's in the list of counters always shown
                if (documentsCountersData[counterName] !== 0 || countersAlwaysDisplayed.includes(counterName)) {
                    documentsCounterEl.closest('.o_portal_index_card').classList.remove('d-none');
                }
            });
            return documentsCountersData;
        });
        return Promise.all(proms).then((results) => {
            this.el.querySelector('.o_portal_doc_spinner').remove();
        });
    },
});

publicWidget.registry.PortalHomeCounters = PortalHomeCounters;

publicWidget.registry.portalSearchPanel = publicWidget.Widget.extend({
    selector: '.o_portal_search_panel',
    events: {
        'click .dropdown-item': '_onDropdownItemClick',
        'submit': '_onSubmit',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._adaptSearchLabel(this.$('.dropdown-item.active'));
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptSearchLabel: function (elem) {
        var $label = $(elem).clone();
        $label.find('span.nolabel').remove();
        this.$('input[name="search"]').attr('placeholder', $label.text().trim());
    },
    /**
     * @private
     */
    _search: function () {
        var search = new URL(window.location).searchParams;
        search.set("search_in", this.$('.dropdown-item.active').attr('href')?.replace('#', '') || "");
        search.set("search", this.$('input[name="search"]').val());
        window.location.search = search.toString();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownItemClick: function (ev) {
        ev.preventDefault();
        var $item = $(ev.currentTarget);
        $item.closest('.dropdown-menu').find('.dropdown-item').removeClass('active');
        $item.addClass('active');

        this._adaptSearchLabel(ev.currentTarget);
    },
    /**
     * @private
     */
    _onSubmit: function (ev) {
        ev.preventDefault();
        this._search();
    },
});
