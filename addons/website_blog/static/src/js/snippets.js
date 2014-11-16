(function() {
    "use strict";

    var website = openerp.website;
    var QWeb = openerp.qweb;
    var _t = openerp._t;
    website.add_template_file('/website_blog/static/src/xml/website_blog.contact_search.xml');

    website.snippet.options.contact_editor = website.snippet.Option.extend({
        start: function () {
            var self = this;
            self.$target.attr('contentEditable', 'false');
            var $btn = $('<div class="dropdown"><a href="#" class="btn btn-default btn-sm search_contact dropdown-toggle" data-toggle="dropdown" title="Search Contact">&nbsp;<i class="fa fa-search"></i>&nbsp;</a></div>');
            self.$overlay.find('.oe_options').after($btn);
            
            $('.search_contact').on('click', function () {
                $(".contact_menu").remove();
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
                    limit: 3,
                    context: website.get_context(),
                }
            }).then(function (result){
                $(".search_contact").after(QWeb.render("blog_contact_search",{contacts:result}));

            }).then(function (){
                $('.xxx').focus();
            }).then(function (){
                $( ".xxx" ).keyup(function(e) {
                        
                    self.name = $('.xxx').val();
                    self.update_existing();
                });
            });
        },

        update_existing: function () {
            var self = this;
            var domain = [];
            console.log(self.name);
            if (self.name && self.name.length) {
                domain.push(['name', 'ilike', self.name]);
            }
                openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'res.partner',
                method: 'search_read',
                args: [domain, ['name']],
                kwargs: {
                    order: 'id desc',
                    limit: 3,
                    context: website.get_context(),
                }
            }).then(function (result){
                $(".yyy").remove();
                $(".zzz").after(QWeb.render("blog_contact_search_update",{contacts:result}));

            });
        }


    });

})();