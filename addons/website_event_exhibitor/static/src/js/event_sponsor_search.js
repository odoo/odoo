odoo.define('website_event_exhibitor.event_sponsor_search', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
publicWidget.registry.websiteEventSearchSponsor = publicWidget.Widget.extend({

    selector: '.o_wesponsor_index',
    events: {
        'click .o_wevent_event_search_box .btn': '_onSearch',
        'click .o_search_tag .btn': '_onTagRemove',
        'click .o_dropdown_reset_tags': '_onTagReset',
        'change .o_wevent_event_tags_form input': '_onTagAdd',
    },

    start: function () {
        this.form = this.$el.find('.o_wevent_event_tags_form');
        return this._super.apply(this, arguments);
    },

    _onSearch: function () {
        const input = this.$el.find('.o_wevent_event_search_box input');
        const params = new URLSearchParams(window.location.search);
        params.set('search', input.val());
        const url = window.location.pathname + '?' + params.toString();
        this.form.attr('action', url);
        this.form.submit();
    },

    _onTagAdd: function () {
        this.form.submit();
    },

    _onTagRemove: function (event) {
        const tag = $(event.target).parent();
        const data = tag.data();
        const selector = 'input[name="' + data.field + '"][value="' + data.value + '"]';
        this._updateFormActionURL(data);
        this.form.find(selector).prop('checked', false);
        this.form.submit();
    },

    _onTagReset: function (event) {
        const dropdown = $(event.target).parent();
        dropdown.find('input').prop('checked', false);
        this.form.submit();
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
            this.form.attr('action', `${window.location.href.split('?')[0]}?${params.toString()}`);
        } catch (e) {
            return;
        }
    },
});

return publicWidget.registry.websiteEventSearchSponsor;
});
