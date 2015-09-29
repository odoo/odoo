odoo.define('website_gengo.website_gengo', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var translate = require('web_editor.translate');
var website = require('website.website');

var qweb = core.qweb;

if (!translate.edit_translations) {
    // Temporary hack until the editor bar is moved to the web client
    return;
}

ajax.loadXML('/website_gengo/static/src/xml/website.gengo.xml', qweb);

website.TopBar.include({
    events: _.extend({}, website.TopBar.prototype.events, {
        'click a[data-action=translation_gengo_post]': 'translation_gengo_post',
        'click a[data-action=translation_gengo_info]': 'translation_gengo_info',
    }),
    edit:function () {
        this.gengo_translate = true;
        this._super.apply(this, arguments);
        var self = this;
        var gengo_langs = ["ar_SY","id_ID","nl_NL","fr_CA","pl_PL","zh_TW","sv_SE","ko_KR","pt_PT","en_US","ja_JP","es_ES","zh_CN","de_DE","fr_FR","fr_BE","ru_RU","it_IT","pt_BR","pt_BR","th_TH","nb_NO","ro_RO","tr_TR","bg_BG","da_DK","en_GB","el_GR","vi_VN","he_IL","hu_HU","fi_FI"];
        if (gengo_langs.indexOf(base.get_context()['lang']) !== -1){
            self.$('.gengo_post,.gengo_wait,.gengo_inprogress,.gengo_info').remove();
            self.$('button[data-action=save]')
            .after(qweb.render('website.ButtonGengoTranslator'));
        }
    },
    translation_gengo_display:function(){
        var self = this;
        if($('[data-oe-translation-state="to_translate"], [data-oe-translation-state="None"]').length === 0){
            self.$el.find('.gengo_post').addClass("hidden");
            self.$el.find('.gengo_inprogress').removeClass("hidden");
        }
    },
    translation_gengo_post: function () {
        var self = this;
        this.new_words =  0;
        $('[data-oe-translation-state="to_translate"], [data-oe-translation-state="None"]').each(function () {
            self.new_words += $(this).text().trim().replace(/ +/g," ").split(" ").length;
        });
        ajax.jsonRpc('/website/check_gengo_set', 'call', {
        }).then(function (res) {
            if (res === 0){
                var dialog = new GengoTranslatorPostDialog(self.new_words);
                dialog.appendTo($(document.body));
                dialog.on('service_level', this, function () {
                    var gengo_service_level = dialog.$el.find(".form-control").val();
                    dialog.$el.modal('hide');
                    self.$el.find('.gengo_post').addClass("hidden");
                    self.$el.find('.gengo_wait').removeClass("hidden");
                    var trans ={}
                    $('[data-oe-translation-state="to_translate"], [data-oe-translation-state="None"]').each(function () {
                        var $node = $(this);
                        var data = $node.data();
                        if (!trans[data.oeTranslationViewId]) {
                            trans[data.oeTranslationViewId] = [];
                        }
                        trans[data.oeTranslationViewId].push({
                            initial_content: qweb.tools.html_escape(self.getInitialContent(this)),
                            new_content: qweb.tools.html_escape(self.getInitialContent(this)),
                            translation_id: data.oeTranslationId || null,
                            gengo_translation: gengo_service_level,
                            gengo_comment:"\nOriginal Page: " + document.URL
                        });
                    });
                    ajax.jsonRpc('/website/set_translations', 'call', {
                        'data': trans,
                        'lang': base.get_context()['lang'],
                    }).then(function () {
                        self.$el.find('.gengo_wait').addClass("hidden");
                        self.$el.find('.gengo_inprogress,.gengo_discard').removeClass("hidden");
                        ajax.jsonRpc('/website/post_gengo_jobs', 'call', {});
                        self.save();
                    }).fail(function () {
                        alert("Could not Post translation");
                    });
                });
            }else{
                var dialog = new GengoApiConfigDialog(res);
                dialog.appendTo($(document.body));
                dialog.on('set_config', this, function () {
                    dialog.$el.modal('hide');
                });
            }
        });
    },
    translation_gengo_info: function () {
        var repr =  $(document.documentElement).data('mainObject');
        var translated_ids = [];
        $('.oe_translatable_text').not(".oe_translatable_inprogress").each(function(){
            translated_ids.push($(this).attr('data-oe-translation-id'));
        });
        ajax.jsonRpc('/website/get_translated_length', 'call', {
            'translated_ids': translated_ids,
            'lang': base.get_context()['lang'],
        }).done(function(res){
            var dialog = new GengoTranslatorStatisticDialog(res);
            dialog.appendTo($(document.body));

        });
    },
});

var GengoTranslatorPostDialog = Widget.extend({
    events: _.extend({}, website.TopBar.prototype.events, {
        'hidden.bs.modal': 'destroy',
        'click button[data-action=service_level]': function () {
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

var GengoTranslatorStatisticDialog = Widget.extend({
    events: _.extend({}, website.TopBar.prototype.events, {
        'hidden.bs.modal': 'destroy',
    }),
    template: 'website.GengoTranslatorStatisticDialog',
    init:function(res){
        var self = this;
        this.inprogess =  0;
        this.new_words =  0;
        this.done =  res.done;
        $('[data-oe-translation-state="to_translate"], [data-oe-translation-state="None"]').each(function () {
            self.new_words += $(this).text().trim().replace(/ +/g," ").split(" ").length;
        });
        $('[data-oe-translation-state="inprogress"]').each(function () {
            self.inprogess += $(this).text().trim().replace(/ +/g," ").split(" ").length;
        });
        this.total = this.done + this.inprogess;
        return this._super.apply(this, arguments);
    },
    start: function (res) {
        this.$el.modal(this.res);
    },
});

var GengoApiConfigDialog = Widget.extend({
    events: _.extend({}, website.TopBar.prototype.events, {
        'hidden.bs.modal': 'destroy',
        'click button[data-action=set_config]': 'set_config'
    }),
    template: 'website.GengoApiConfigDialog',
    init:function(company_id){
        this.company_id =  company_id;
        return this._super.apply(this, arguments);
    },
    start: function (res) {
        this.$el.modal(this.res);
    },
    set_config:function(){
       var self = this;
       var public_key = this.$el.find("#gengo_public_key")[0].value;
       var private_key = this.$el.find("#gengo_private_key")[0].value;
       var auto_approve = this.$el.find("#gengo_auto_approve")[0].checked;
       var sandbox = this.$el.find("#gengo_sandbox")[0].checked;
       var pub_el = this.$el.find(".gengo_group_public")[0];
       var pri_el = this.$el.find(".gengo_group_private")[0];
       if(! public_key){
           $(pub_el).addClass("has-error");
       }
       else{
           $(pub_el).removeClass("has-error");
       }
       if(! private_key){
           $(pri_el).addClass("has-error");
       }
       else{
           $(pri_el).removeClass("has-error");
       }
       if(public_key && private_key){
           ajax.jsonRpc('/website/set_gengo_config', 'call', {
               'config': {'gengo_public_key':public_key,'gengo_private_key':private_key,'gengo_auto_approve':auto_approve,'gengo_sandbox':sandbox},
           }).then(function () {
               self.trigger('set_config');
           }).fail(function () {
               alert("Could not submit ! Try Again");
           });
       }
    }
});

});
