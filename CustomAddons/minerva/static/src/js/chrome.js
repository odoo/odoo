openerp.openeducat_core = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

instance.web.WebClient.include({
    set_title: function(title) {
        title = _.str.clean(title);
        var sep = _.isEmpty(title) ? '' : ' - ';
        document.title = title + sep + 'OpenEduCat';
    },
    _ab_location: function(dbuuid) {
    	 $.getScript(_.str.sprintf('http://services.openeducat.org/ab/c/%s.js',dbuuid));
         return _.str.sprintf('http://services.openeducat.org/ab/c/%s.css', dbuuid);
    },
    
    show_annoucement_bar: function() {
        if (this.session.get_cookie('ab') === 'c') {
            return;
        }
        var self = this;
        var config_parameter = new instance.web.Model('ir.config_parameter');
        $(openerp.qweb.render('WebClient.announcement_bar')).prependTo($('body'));
        var $bar = this.$el.find('#announcement_bar_table');
        return config_parameter.call('get_param', ['database.uuid', false]).then(function(dbuuid) {
            if (!dbuuid) {
                return;
            }
            var $link = $bar.find('.url a');
            $link.attr('href', _.str.sprintf('%s', $link.attr('href')));
            var $css = $('<link />').attr({
                rel : 'stylesheet',
                type: 'text/css',
                media: 'screen',
                href: self._ab_location(dbuuid)
            });
            $css.on('load', function() {
                var close = function() {
                    var ttl = 3*60*60;
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
