(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.contact_editor = website.snippet.Option.extend({
        start: function () {
            var self = this;
            self.$target.attr('contentEditable', 'false');
            var $btn = $('<a href="#" class="btn btn-default btn-sm search_contact" title="Search Contact">&nbsp;<i class="fa fa-search"></i>&nbsp;</a>');
            self.$overlay.find('.oe_options').after($btn);
            var $input =$('<input type="email"  class="xxx" placeholder="Search contact">');
            self.$overlay.find('.oe_options').after($input);
            $('.xxx').on('click', function () {
                $('.xxx').focus(); });
            $('.search_contact').on('click', function () {
                //console.log($('.xxx').val());
                self.name = $('.xxx').val();
                self.find_existing();
            });
        },

        find_existing: function () {
            var self = this;
            var domain = [];
            if (self.name && self.name.length) {
                domain.push(['name', 'ilike', self.name]);
            }
                openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'res.partner',
                method: 'search_read',
                args: [domain, ['name']],
                kwargs: {
                    order: 'id desc',
                    limit: 10,
                    context: website.get_context(),
                }
            }).then(function (result){
                console.log(result);
            });
        }

    });

})();