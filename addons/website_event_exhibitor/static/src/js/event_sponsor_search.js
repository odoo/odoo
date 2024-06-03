/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
publicWidget.registry.websiteEventSearchSponsor = publicWidget.Widget.extend({

    selector: '.o_wesponsor_index',
    events: {
        'click .o_wevent_event_search_box .btn': '_onSearch',
        'click .o_search_tag .btn': '_onTagRemove',
        'click .o_dropdown_reset_tags': '_onTagReset',
        'change .o_wevent_event_tags_form input': '_onTagAdd',
        'change .o_wevent_event_tags_mobile_form input': '_onTagAddMobile',
    },

    start: function () {
        this.formEl = this.el.querySelector(".o_wevent_event_tags_form");
        this.mobileFormEl = this.el.querySelector(".o_wevent_event_tags_mobile_form");
        return this._super.apply(this, arguments);
    },

    _onSearch: function () {
        const inputEl = this.el.querySelector(".o_wevent_event_search_box input");
        const params = new URLSearchParams(window.location.search);
        params.set("search", inputEl.value);
        const url = window.location.pathname + '?' + params.toString();
        this.formEl.action = url;
        this.formEl.submit();
    },

    _onTagAdd: function () {
        this.formEl.submit();
    },

    _onTagAddMobile: function () {
        this.mobileFormEl.submit();
    },

    _onTagRemove: function (event) {
        const tagEl = event.target.parentNode;
        const data = tagEl.dataset;
        const selector = 'input[name="' + data.field + '"][value="' + data.value + '"]';
        this._updateFormActionURL(data);
        this.formEl.querySelector(selector).checked = false;
        this.formEl.submit();
    },

    _onTagReset: function (event) {
        const dropdownEl = event.target.parentNode;
        dropdownEl.querySelectorAll("input").forEach((inputEl) => (inputEl.checked = false));
        this.formEl.submit();
    },

    _updateFormActionURL: function (data) {
        const mapping = new Map([
            ['sponsor_country', 'countries'],
            ['sponsor_type', 'sponsorships']
        ]);
        if (!mapping.has(data.field)) {
            return
        }
        const name = mapping.get(data.field);
        const params = new URLSearchParams(window.location.search);
        try {
            const ids = JSON.parse(params.get(name));
            params.set(name, JSON.stringify(ids.filter(id => id !== data.value)));
            this.formEl.action = `${window.location.href.split("?")[0]}?${params.toString()}`;
        } catch {
            return;
        }
    },
});

export default publicWidget.registry.websiteEventSearchSponsor;
