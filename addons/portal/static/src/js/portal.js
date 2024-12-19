import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'change select[name="country_id"]': '_onCountryChange',
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
        var nb = $displayedState.appendTo(this.$state).removeClass('d-none').show().length;
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
});

publicWidget.registry.portalPicture = publicWidget.Widget.extend({
    selector: ".o_portal_picture_card",
    events: {
        "click .o_portal_profile_pic_edit": "_onEditProfilePicClick",
        "click .o_portal_profile_pic_clear": "_onProfilePicClearClick",
        "change .o_file_upload": "_onFileUploadChange",
    },

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEditProfilePicClick: function (ev) {
        ev.preventDefault();
        const pictureCardEl = ev.currentTarget.closest(".o_portal_picture_card");
        pictureCardEl.querySelector(".o_file_upload")?.click();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFileUploadChange: function (ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        const pictureCardEl = ev.currentTarget.closest(".o_portal_picture_card");
        const currentValue = pictureCardEl.querySelector(".o_wportal_avatar_img").value;
        const reader = new FileReader();
        const file = ev.currentTarget.files[0];
        reader.onload = (ev) => {
            const img = new Image();
            img.onload = () => {
                pictureCardEl.querySelector(".o_wportal_avatar_img").src = ev.target.result;
                pictureCardEl.querySelector("input#remove_profile")?.remove();
            };
            img.onerror = () => {
                this.notification.add(_t("The selected image is broken or invalid."), {
                    type: "danger",
                });
                pictureCardEl.querySelector("input[type=file]").value = null;
                pictureCardEl.querySelector(".o_wportal_avatar_img").src = currentValue;
            };

            img.src = ev.target.result;
        };
        reader.onerror = () => {
            this.notification.add(_t("Failed to read the selected image."), {
                type: "danger",
            });
        };

        reader.readAsDataURL(file);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        ev.preventDefault();
        const pictureCardEl = ev.currentTarget.closest(".o_portal_picture_card");

        const removeProfileInput = pictureCardEl.querySelector("input#remove_profile");
        const clearImageInput = pictureCardEl.querySelector("input#forum_clear_image");
        if (!removeProfileInput && !clearImageInput) {
            pictureCardEl.querySelector(".o_wportal_avatar_img").src =
                "/web/static/img/placeholder.png";

            const inputElement = document.createElement("input");
            inputElement.type = "hidden";
            Object.assign(
                inputElement,
                this.target.querySelector("span")?.textContent === "Public Profile"
                    ? { name: "clear_image", id: "forum_clear_image" }
                    : { name: "remove_profile", id: "remove_profile", value: "true" }
            );
            pictureCardEl.appendChild(inputElement);
        }
    },
});

export default publicWidget.registry.portalDetails;

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
