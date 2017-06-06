openerp.download_action = function (instance) {

    console.log("Download action: loaded");

    var trigger_download = function(session, response, c) {
        session.get_file({
            url: '/download',
            data: {data: JSON.stringify(response)},
            complete: openerp.web.unblockUI,
            error: c.rpc_error.bind(c)
        });
    }

    instance.web.ActionManager = instance.web.ActionManager.extend({
        ir_actions_download: function (action, options) {
            var c = openerp.webclient.crashmanager;
            instance.web.blockUI();
            trigger_download(this.session, action, c);
        }
    });
};
