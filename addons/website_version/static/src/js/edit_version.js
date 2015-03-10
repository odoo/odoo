odoo.define('website_version.edit', ['web.ajax', 'web.core', 'website.editor'], function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var editor = require('website.editor');

var _t = core._t;
var qweb = core.qweb;

editor.EditorBar.include({
    start: function() {
        var self = this;
        this.$el.on('click', '#save_as_new_version', function() {

            var wizardA = $(qweb.render("website_version.new_version",{'default_name': moment().format('L')}));
            wizardA.appendTo($('body')).modal({"keyboard" :true});
            wizardA.on('click','.o_create', function(){
                wizardA.find('.o_message').remove();
                var version_name = wizardA.find('.o_version_name').val();
                if(version_name.length === 0){
                    wizardA.find(".o_version_name").after("<p class='o_message' style='color : red'> *"+_t("This field is required")+"</p>");
                }
                else{
                    wizardA.modal("hide");
                    ajax.jsonRpc( '/website_version/create_version', 'call', { 'name': version_name, 'version_id': 0}).then(function (result) {
                        $('html').data('version_id', result);
                        var wizard = $(qweb.render("website_version.dialogue",{message:_.str.sprintf("You are now working on version: %s.", version_name),
                                                                                   dialogue:_.str.sprintf("If you edit this page or others, all changes will be recorded in the version. It will not be visible by visitors until you publish the version.")}));
                        wizard.appendTo($('body')).modal({"keyboard" :true});
                        wizard.on('click','.o_confirm', function(){
                            self.save();
                        });
                        wizard.on('hidden.bs.modal', function () {$(this).remove();});
                    }).fail(function(){
                        var wizard = $(qweb.render("website_version.message",{message:_t("This name already exists.")}));
                        wizard.appendTo($('body')).modal({"keyboard" :true});
                        wizard.on('hidden.bs.modal', function () {$(this).remove();});
                    });
                }
            });
            wizardA.on('hidden.bs.modal', function () {$(this).remove();});

        });
        this.$el.on('click', '#save_and_publish', function() {
            var version_id = parseInt($('html').data('version_id'));
            if(version_id)
            {
                self.save();
            }
            else
            {
                var wizard = $(qweb.render("website_version.publish",{message:_t("Are you sure you want to publish your modifications.")}));
                wizard.appendTo($('body')).modal({"keyboard" :true});
                wizard.on('click','.o_confirm', function(){
                    self.save();
                });
                wizard.on('hidden.bs.modal', function () {$(this).remove();});
            }

        });

        $('.option_choice').click(function() {
            self.$el.find(".o_second_choice").remove();
            var name = $('#version-menu-button').data('version_name');
            if(name){
                self.$el.find(".o_first_choice").before(qweb.render("all_options", {version:'Save on '+name}));
            }
            else{
                self.$el.find(".o_first_choice").before(qweb.render("all_options", {version:'Save and Publish'}));
            }

        });

        return this._super();
    }
});


});
