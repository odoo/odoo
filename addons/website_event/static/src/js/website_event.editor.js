(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        new_event: function() {
            website.prompt({
                id: "editor_new_event",
                window_title: _t("New Event"),
                input: "Event Name",
            }).then(function (event_name) {
                website.form('/event/add_event', 'POST', {
                    event_name: event_name
                });
            });
        },
    });
})();
