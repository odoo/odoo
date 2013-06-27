(function() {
    // Init headless webclient
    // TODO: Webclient research : use iframe embedding mode
    //       Meanwhile, let's HACK !!!
    var $web = $('<div style="display: none;"/>').appendTo('body');
    var s = new openerp.init(['web']);
    s.web.WebClient.bind_hashchange = s.web.blockUI = s.web.unblockUI = function() {};
    s.web.WebClient.include({ do_push_state: function() {} });
    var wc = new s.web.WebClient();
    wc.appendTo($web);
    var instance = openerp.instances[wc.session.name];

    setTimeout(function () {
        // HACKY HACK YUCK YUCK !!
        // TODO: Need modification to webclient. Webclient shall trigger an event when it's ready.
        //       Maybe notification shall trigger event too, so the host can bind on it and use
        //       it's own means in order to trigger it's own notification !?
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
