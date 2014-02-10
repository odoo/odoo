(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_event/static/src/xml/website_event.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap.js_event").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_event]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_event",
                    window_title: _t("New Event"),
                    input: "Event Name",
                }).then(function (event_name) {
                    website.form('/event/add_event', 'POST', {
                        event_name: event_name
                    });
                });
            }
        }),
    });
})();
