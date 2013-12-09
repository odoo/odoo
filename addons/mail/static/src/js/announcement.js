openerp_announcement = function(instance) {
    instance.web.WebClient.include({
        show_application: function() {
            return $.when(this._super.apply(this, arguments)).then(this.proxy('show_annoucement_bar'));
        },
        _ab_location: function(dbuuid) {
            return _.str.sprintf('https://services.openerp.com/openerp-enterprise/ab/css/%s.css', dbuuid);
        },
        show_annoucement_bar: function() {
            if (this.session.get_cookie('ab') === 'c') {
                return;
            }
            var self = this;
            var config_parameter = new instance.web.Model('ir.config_parameter');
            var $bar = this.$el.find('.announcement_bar');
            return config_parameter.call('get_param', ['database.uuid', false]).then(function(dbuuid) {
                if (!dbuuid) {
                    return;
                }
                var $css = $('<link />').attr({ 
                    rel : 'stylesheet',
                    type: 'text/css',
                    media: 'screen',
                    href: self._ab_location(dbuuid)
                });
                $css.on('load', function() {
                    var close = function() {
                        var data = window.getComputedStyle($bar.find('.data')[0], ':before').content || "'{}'";
                        var delim = data[0];
                        data = data.slice(1, data.length - 1).replace(new RegExp('\\\\'+delim, 'g'), delim);
                        try {
                            data = JSON.parse(data);
                        } catch(_e) {
                            data = {};
                        }
                        var ttl = data.close_ttl || 24*60*60;
                        self.session.set_cookie('ab', 'c', ttl);

                        $bar.slideUp('slow');
                    };
                    $bar.find('.close').on('click', close);
                    self.trigger('ab_loaded', $bar);
                });

                $('head').append($css);
            });
        }
    });
};
