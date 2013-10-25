openerp_announcement = function(instance) {
	var _t = instance.web._t;
	instance.web.WebClient.include({
		show_application: function() {
            var self = this;
            this._super();
            var config_parameter = new instance.web.Model('ir.config_parameter');
            return config_parameter.call('get_param', ['database.uuid', false]).then(function(result) {
                var head  = $('head');
                head.append($('<link />')
                    .attr({ 
                        rel : 'stylesheet',
                        type: 'text/css',
                        href: 'http://127.0.0.1.xip.io:8369/openerp_enterprise/'+result+'.css',
                        media: 'all',
                    })
                );
            });
        },
    });
};