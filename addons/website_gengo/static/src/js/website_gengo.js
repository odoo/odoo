(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website_gengo/static/src/xml/website.gengo.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=translation_gengo]': 'translation_gengo',
            'click a[data-action=translation_gengo_post]': 'translation_gengo_post',
        }),
        start: function () {
            this.gengo_translate = false;
            this._super.apply(this, arguments);
            var self = this;
            self.$('button[data-action=edit]')
                .after(openerp.qweb.render('website.ButtonGengoTranslator'));
        },
        translation_gengo: function () {
            var self = this;
            var dialog = new website.GengoTranslatorDialog();
            dialog.appendTo($(document.body));
            self.gengo_translate = true;
            dialog.on('activate', this, function () {
                dialog.$el.modal('hide');
                self.translate().then(function () {
                    self.gengo_translate = false;
                    self.$el.find('.gengo_translate').addClass("hidden");
                    self.$el.find('.gengo_post').removeClass("hidden");
                });
            });
            
        },
        translation_gengo_post: function () {
            var self = this;
            var translatable_list = $.find('.oe_translatable_todo');
            var dialog = new website.GengoTranslatorPostDialog();
            dialog.appendTo($(document.body));
            dialog.on('service_level', this, function () {
                var gengo_service_level = dialog.$el.find(".form-control").val();
                dialog.$el.modal('hide');
                var trans ={}
                $('.oe_translatable_todo').each(function () {
                    var $node = $(this);
                    var data = $node.data();
                    if (!trans[data.oeTranslationViewId]) {
                        trans[data.oeTranslationViewId] = [];
                    }
                    trans[data.oeTranslationViewId].push({
                        initial_content: self.getInitialContent(this),
                        new_content:self.getInitialContent(this),
                        translation_id: data.oeTranslationId || null,
                        gengo_translation: gengo_service_level
                    });
                });
                openerp.jsonRpc('/website/set_translations', 'call', {
                    'data': trans,
                    'lang': website.get_context()['lang'],
                });
            });
            
        },
    });
    
    website.GengoTranslatorDialog = openerp.Widget.extend({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'hidden.bs.modal': 'destroy',
            'click button[data-action=activate]': function (ev) {
                this.trigger('activate');
            },
        }),
        template: 'website.GengoTranslatorDialog',
        start: function () {
            this.$el.modal();
        },
    });
    
    website.GengoTranslatorPostDialog = openerp.Widget.extend({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'hidden.bs.modal': 'destroy',
            'click button[data-action=service_level]': function (ev) {
                this.trigger('service_level');
            },
        }),
        template: 'website.GengoTranslatorPostDialog',
        start: function () {
            this.$el.modal();
        },
    });

})();
