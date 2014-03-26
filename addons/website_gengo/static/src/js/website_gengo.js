(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website_gengo/static/src/xml/website.gengo.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=translation_gengo_post]': 'translation_gengo_post',
            'click a[data-action=translation_gengo_info]': 'translation_gengo_info',
        }),
        edit:function () {
            this.gengo_translate = true;
            this._super.apply(this, arguments);
            var self = this;
            var gengo_langs = ["ar_SA","id_ID","nl_NL","fr_CA","pl_PL","zh_TW","sv_SE","ko_KR","pt_PT","en_US","ja_JP","es_ES","zh_CN","de_DE","fr_FR","fr_BE","ru_RU","it_IT","pt_BR"];
            if (gengo_langs.indexOf(website.get_context()['lang']) != -1){   
                self.$('button[data-action=save]')
                .after(openerp.qweb.render('website.ButtonGengoTranslator'));
            }
        },
        translation_gengo_display:function(){
            var self = this;
            if($('.oe_translatable_todo').length == 0){
                self.$el.find('.gengo_post').addClass("hidden");
                self.$el.find('.gengo_inprogress').removeClass("hidden");
            }
        },
        translation_gengo_post: function () {
            var self = this;
            var translatable_list = $.find('.oe_translatable_todo');
            this.new_words =  0;
            $('.oe_translatable_todo').each(function () {
                self.new_words += $(this).text().trim().replace(/ +/g," ").split(" ").length;
            });
            openerp.jsonRpc('/website/check_gengo_set', 'call', {
            }).then(function (res) {
                if (res == 0){
                    var dialog = new website.GengoTranslatorPostDialog(self.new_words);
                    dialog.appendTo($(document.body));
                    dialog.on('service_level', this, function () {
                        var gengo_service_level = dialog.$el.find(".form-control").val();
                        dialog.$el.modal('hide');
                        self.$el.find('.gengo_post').addClass("hidden");
                        self.$el.find('.gengo_wait').removeClass("hidden");
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
                                gengo_translation: gengo_service_level,
                                gengo_comment:"Original page:" + document.URL
                            });
                        });
                        openerp.jsonRpc('/website/set_translations', 'call', {
                            'data': trans,
                            'lang': website.get_context()['lang'],
                        }).then(function () {
                            $('.oe_translatable_todo').addClass('oe_translatable_inprogress').removeClass('oe_translatable_todo');
                            self.$el.find('.gengo_wait').addClass("hidden");
                            self.$el.find('.gengo_inprogress,.gengo_discard').removeClass("hidden");
                            self.save();
                        }).fail(function () {
                            alert("Could not Post translation");
                        });
                    });
                }else{
                    var dialog = new website.GengoApiConfigDialog(res);
                    dialog.appendTo($(document.body));
                }
            });
            
        },
        translation_gengo_info: function () {
            var repr =  $(document.documentElement).data('mainObject');
            var view_id = repr.match(/.+\((.+), (\d+)\)/)[2];
            var translated_ids = [];
            $('.oe_translatable_text').not(".oe_translatable_inprogress").each(function(){
                translated_ids.push($(this).attr('data-oe-translation-id'));
            });
            openerp.jsonRpc('/website/get_translated_length', 'call', {
                'translated_ids': translated_ids,
                'lang': website.get_context()['lang'],
            }).done(function(res){
                var dialog = new website.GengoTranslatorStatisticDialog(res);
                dialog.appendTo($(document.body));
                
            });
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
        init:function(new_words){
            this.new_words = new_words;
            return this._super.apply(this, arguments);
        },
        start: function () {
            this.$el.modal();
        },
    });
    
    website.GengoTranslatorStatisticDialog = openerp.Widget.extend({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'hidden.bs.modal': 'destroy',
        }),
        template: 'website.GengoTranslatorStatisticDialog',
        start: function (res) {
            this.$el.modal(this.res);
        },
    });
    website.GengoApiConfigDialog = openerp.Widget.extend({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'hidden.bs.modal': 'destroy',
        }),
        template: 'website.GengoApiConfigDialog',
        init:function(company_id){
            this.company_id =  company_id;
            return this._super.apply(this, arguments);
        },
        start: function (res) {
            this.$el.modal(this.res);
        },
    });

})();
