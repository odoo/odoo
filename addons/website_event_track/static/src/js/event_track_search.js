import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteEventSearchTrack = publicWidget.Widget.extend({
    selector: '.o_wevent_event_track_search_box',
    events: {
        'search .search-query': '_onSearch',
    },

    _onSearch: function () {
        const input = this.el.querySelector('input.search-query');
        if(!input.value) {
            this.el.querySelector('form.o_wevent_event_searchbar_form')?.submit();
        }
    }
});
