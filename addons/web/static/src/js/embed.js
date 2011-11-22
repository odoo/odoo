openerp.web.embed = function(session) {

    session.util = session.util || {}
    session.util.currentScript = function() {
        var currentScript = document.currentScript;
        if (!currentScript) {
            var sc = document.getElementsByTagName('script');
            currentScript = sc[sc.length-1];
        }
        return currentScript;
    };


    /*
    session.connection.on_session_invalid.add_last(function() {
        console.error("invalid session", arguments);
    });
    // */

    
    session.web.EmbedClient = session.web.Widget.extend({
        template: 'EmptyComponent',
        init: function(action_id) {
            this._super();
            this.action_id = action_id;
            this.am = new session.web.ActionManager();
        },

        start: function() {
            var self = this;

            this.am.appendTo(this.$element.addClass('openerp'));

            return this.rpc("/web/action/load", { action_id: this.action_id }, function(result) {
                var action = result.result;
                action.flags = _.extend({
                    //views_switcher : false,
                    search_view : false,
                    action_buttons : false,
                    sidebar : false
                    //pager : false
                }, action.flags || {});

                self.am.do_action(action);
            });
        },

    });
};
