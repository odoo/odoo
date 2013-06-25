(function() {
    // Init headless webclient
    // TODO: check embedded mode or how to put it cleanly in a dom ready callback
    var $web = $('<div style="display: none;"/>').appendTo('body');
    var s = new openerp.init(['web']);
    var wc = new s.web.WebClient();
    // TODO: disable blockUI
    wc.appendTo($web);
    var instance = openerp.instances[wc.session.name];

    setTimeout(function () {
        // HACKY HACK YUCK YUCK !!
        // TODO: Need modification to webclient. Webclient shall trigger an event when it's ready.
        if (instance.web.notification) {
            instance.web.notification.$el.appendTo('body');
        } else {
            console.log("too late");
        }
    }, 2000);

    $(function() {
        $('.editable').css('outline', '1px dotted red').attr('contentEditable', 'true').click(function (e) {
            e.stopPropagation();
            e.preventDefault();
        });
        $('body').on("keypress", ".editable", function(e) {
            if (e.which == 13) {
                var $el = $(e.currentTarget);
                var data = $el.data();
                var update = {};
                // TODO: Are we going to use a meta-data flag in order to know if the field shall be text or html ?
                update[data.field] = $el.text();
                (new instance.web.DataSet(this, data.model)).write(data.id, update).done(function() {
                    $el.blur();
                    instance.webclient.do_notify('Save', _.str.sprintf('%s#%d#%s saved', data.model, data.id, data.field));
                }).fail(function () {
                    console.error('fail');
                });
                e.preventDefault();
            }
        });
    });
})();
