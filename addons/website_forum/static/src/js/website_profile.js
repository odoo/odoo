import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteProfileForumActivities = publicWidget.Widget.extend({
    selector: '.o_wprofile_forum_activities',
    read_events: {
        'click #profile_extra_info_activities_filter li a': '_onSelectTab',
    },

    /**
     * @override
     */
    start: function () {
        this.formSelectorByTabRef = {
            "#profile_extra_info_activities_tab_question": ".o_wprofile_forum_activities_search_question",
            "#profile_extra_info_activities_tab_answer": ".o_wprofile_forum_activities_search_answer",
        };
        const activeTab = this.$el.data('active-tab');
        this._selectTab(document.querySelector(`a[href="#profile_extra_info_activities_tab_${activeTab}"]`));
    },

    _onSelectTab: function (ev) {
        this._selectTab(ev.target);
    },

    _selectTab: function(navLink) {
        const selectedTabRef = navLink.getAttribute("href");
        for (const [tabRef, formSelector] of Object.entries(this.formSelectorByTabRef)) {
            const form = document.querySelector(formSelector);
            if (tabRef === selectedTabRef) {
                form.classList.remove("d-none");
            } else {
                form.classList.add("d-none");
            }
        }
        document.querySelector(".profile_extra_info_activities_filter_label").textContent = navLink.text;
    }
});
