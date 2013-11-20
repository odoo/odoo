(function() {
    "use strict";

    var website = openerp.website;
    website.add_template_file('/website_event/static/src/xml/website_event.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_event]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    window_title: "New Event",
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
