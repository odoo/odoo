odoo.define('website_version.menu', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');

var _t = core._t;
var qweb = core.qweb;

var _get_context = base.get_context;
base.get_context = function (dict) {
    return _.extend({ 'version_id': $("#version-menu-button").data("version_id")|0 }, _get_context(dict));
};

ajax.loadXML('/website_version/static/src/xml/version_templates.xml', qweb);

var EditorVersion = Widget.extend({
    start: function() {
        var self = this;
        self.$el.on('click', 'a[data-action]', function(ev) {
            ev.preventDefault();
            self[$(this).data('action')](ev);
        });

        this.$el.find('#version-menu-button').click(function() {
            var view_id = parseInt($('html').attr('data-view-xmlid'));
            ajax.jsonRpc( '/website_version/all_versions', 'call', {'view_id': view_id}).then(function (result) {
                self.$el.find(".o_version_choice").remove();
                self.$el.find(".first_divider").before(qweb.render("website_version.all_versions", {versions:result}));

            });
            ajax.jsonRpc( '/website_version/has_experiments', 'call', {'view_id': view_id}).then(function (result) {
                self.$el.find(".o_experiment").remove();
                if(result){
                    self.$el.find(".create_experiment").after(qweb.render("website_version.experiment_menu"));
                }
            });
            
        });
        return this._super();
    },
    
    duplicate_version: function(event) {
        var version_id = base.get_context().version_id;
        var wizardA = $(qweb.render("website_version.new_version",{'default_name': moment().format('L')}));
        wizardA.appendTo($('body')).modal({"keyboard" :true});
        wizardA.on('click','.o_create', function(){
            wizardA.find('.o_message').remove();
            var version_name = wizardA.find('.o_version_name').val();
            if(version_name.length == 0){
                wizardA.find(".o_version_name").after("<p class='o_message' style='color : red'> *"+_t("This field is required")+"</p>");
            }
            else{
                wizardA.modal("hide");
                ajax.jsonRpc( '/website_version/create_version', 'call', { 'name': version_name, 'version_id': version_id}).then(function (result) {

                    var wizard = $(qweb.render("website_version.dialogue",{message:_.str.sprintf("You are now working on version: %s.", version_name),
                                                                                   dialogue:_.str.sprintf("If you edit this page or others, all changes will be recorded in the version. It will not be visible by visitors until you publish the version.")}));
                    wizard.appendTo($('body')).modal({"keyboard" :true});
                    wizard.on('click','.o_confirm', function(){
                        window.location.href = '\?enable_editor';
                    });
                    wizard.on('hidden.bs.modal', function () {$(this).remove();});
                }).fail(function(){
                    var wizard = $(qweb.render("website_version.message",{message:_t("This name already exists.")}));
                    wizard.addClass("o_error");
                    wizard.appendTo($('body')).modal({"keyboard" :true});
                    wizard.on('hidden.bs.modal', function () {$(this).remove();});
                });
            }
        });
        wizardA.on('hidden.bs.modal', function () {$(this).remove();});
    },
    
    change_version: function(event) {
        var version_id = parseInt($(event.target).closest("li").data("version_id"));
        if(! version_id){
            version_id = 0;//By default master
        }
        ajax.jsonRpc( '/website_version/change_version', 'call', { 'version_id':version_id }).then(function (result) {
                location.reload();
            });
    },

    delete_version: function(event) {
        var version_id = parseInt($(event.target).closest("li").data("version_id"));
        var name = $(event.currentTarget).parent().children(':last-child').text();
        ajax.jsonRpc( '/website_version/check_version', 'call', { 'version_id':version_id }).then(function (result) {
                if (result){
                    var wizard = $(qweb.render("website_version.message",{message:_.str.sprintf("You cannot delete the %s version because it is in a running or paused experiment", name)}));
                    wizard.appendTo($('body')).modal({"keyboard" :true});
                    wizard.on('hidden.bs.modal', function () {$(this).remove();});
                }
                else{
                    var wizardA = $(qweb.render("website_version.delete_message",{message:_.str.sprintf("Are you sure you want to delete the %s version ?", name)}));
                    wizardA.appendTo($('body')).modal({"keyboard" :true});
                    wizardA.on('click','.o_confirm', function(){
                        ajax.jsonRpc( '/website_version/delete_version', 'call', { 'version_id':version_id }).then(function (result) {
                            var wizardB = $(qweb.render("website_version.message",{message:_.str.sprintf("The %s version has been deleted.", result)}));
                            wizardB.appendTo($('body')).modal({"keyboard" :true});
                            wizardB.on('click','.o_confirm', function(){
                                location.reload();
                            wizardB.on('hidden.bs.modal', function () {$(this).remove();});
                            });
                        });
                    });
                    wizardA.on('hidden.bs.modal', function () {$(this).remove();});
                }
            });
    },

    publish_version: function(event) {
        var version_id = base.get_context().version_id;
        var name = $('#version-menu-button').attr('data-version_name');
        ajax.jsonRpc( '/website_version/diff_version', 'call', { 'version_id':version_id}).then(function (result) {
            var wizardA = $(qweb.render("website_version.publish_message",{message:_.str.sprintf("Publish Version %s", name), list:result}));
            wizardA.appendTo($('body')).modal({"keyboard" :true});
            wizardA.on('click','.o_confirm', function(){
                wizardA.find('.o_message').remove();
                var check = wizardA.find('.o_check').is(':checked');
                var copy_master_name = wizardA.find('.o_name').val();
                if(check){
                    if(copy_master_name.length == 0){
                        wizardA.find(".o_name").after("<p class='o_message' style='color : red'> *"+_t("This field is required")+"</p>");
                    }
                    else{
                        ajax.jsonRpc( '/website_version/publish_version', 'call', { 'version_id':version_id, 'save_master':true, 'copy_master_name':copy_master_name}).then(function (result) {
                            var wizardB = $(qweb.render("website_version.dialogue",{message:_.str.sprintf("The %s version has been published", result), dialogue:_.str.sprintf("The master has been saved on a new version called %s.",copy_master_name)}));
                            wizardB.appendTo($('body')).modal({"keyboard" :true});
                            wizardB.on('click','.o_confirm', function(){
                                location.reload();
                            });
                            wizardB.on('hidden.bs.modal', function () {$(this).remove();});
                        });
                    }
                }
                else{
                    ajax.jsonRpc( '/website_version/publish_version', 'call', { 'version_id':version_id, 'save_master':false, 'copy_master_name':""}).then(function (result) {
                        var wizardC = $(qweb.render("website_version.message",{message:_.str.sprintf("The %s version has been published.", result)}));
                        wizardC.appendTo($('body')).modal({"keyboard" :true});
                        wizardC.on('click','.o_confirm', function(){
                            location.reload();
                        });
                        wizardC.on('hidden.bs.modal', function () {$(this).remove();});
                    });
                }
            });
            wizardA.on('click','input[name="optionsRadios"]', function(){
                wizardA.find('.o_message').remove();
                wizardA.find('.o_name').toggle( wizardA.find('.o_check').is(':checked') );
            });
            wizardA.on('hidden.bs.modal', function () {$(this).remove();});
        });
    },

    diff_version: function(event) {
        var version_id = base.get_context().version_id;
        var name = $('#version-menu-button').data('version_name');
        ajax.jsonRpc( '/website_version/diff_version', 'call', { 'version_id':version_id}).then(function (result) {
            var wizard = $(qweb.render("website_version.diff",{list:result, version_name:name}));
            wizard.appendTo($('body')).modal({"keyboard" :true});
            wizard.on('click','.o_confirm', function(){});
            wizard.on('hidden.bs.modal', function () {$(this).remove();});
        });
    },

    google_analytics: function(event){
        window.location.href = 'https://www.google.com/analytics/web';

    },

    create_experiment: function() {
        var self = this;
        var view_id = parseInt($('html').attr('data-view-xmlid'));
        ajax.jsonRpc( '/website_version/all_versions_all_goals', 'call', { 'view_id': view_id }).then(function (result) {
            var wizardA = $(qweb.render("website_version.create_experiment",{versions:result.tab_version, goals:result.tab_goal, config:result.check_conf}));
            wizardA.appendTo($('body')).modal({"keyboard" :true});
        
            wizardA.on('click','.o_launch', function(){
                wizardA.find('.o_message').remove();
                var name = wizardA.find('.o_name').val();
                var tab = wizardA.find('.o_version');
                var result = [];
                var i;
                for (var i = 0; i < tab.length; i++){
                    if ($(tab[i]).is(':checked')) {
                        result.push(parseInt($(tab[i]).attr('data-version_id')));
                    }
                }
                var goal_id = wizardA.find('.box').val();
                var check = true;
                if (name.length == 0){
                    wizardA.find(".o_name").after("<p class='o_message' style='color : red'> *"+_t("This field is required")+"</p>");
                    check = false;
                }
                if (result.length == 0 && check){
                    wizardA.find(".o_versions").after("<p class='o_message' style='color : red'> *"+_t("You must select at least one version which is not Master.")+"</p>");
                    check = false;
                }
                if(check){
                    ajax.jsonRpc( '/website_version/launch_experiment', 'call', { 'name':name, 'version_ids':result, 'goal_id':goal_id }).then(function (existing_experiment) {
                        if (!existing_experiment['existing']){
                            var wizardB = $(qweb.render("website_version.dialogue",{message:_.str.sprintf("Your %s experiment is created.", name), dialogue:_t(" Now you can manage this experiment by clicking on Manage A/B tests.")}));
                            wizardB.appendTo($('body')).modal({"keyboard" :true});
                            wizardB.on('click','.o_confirm', function(){
                                location.reload();
                            });
                            wizardB.on('hidden.bs.modal', function () {$(this).remove();});

                        }
                        else{
                            if(existing_experiment['existing'] == 1){
                                wizardA.find(".o_versions").after("<p class='o_message' style='color : red'> *"+_.str.sprintf("Your %s experiment cannot be launched because this experiment contains a view which is already used in the running %s experiment.", name, existing_experiment['name'])+"</p>");
                            }
                            else{
                                wizardA.find(".o_versions").after("<p class='o_message' style='color : red'> *"+_.str.sprintf("You cannot have more then 24 running/paused experiments.")+"</p>");
                            }
                        }
                    });
                }
            });
            wizardA.on('click','.o_configure', function(){
                var website_id = $('html').attr('data-website-id');
                window.location.href ='/web#id='+website_id+'&view_type=form&model=website&action=website_version.action_website_view';
            });
            wizardA.on('click','.o_validate_0', function(){
                wizardA.find('.o_message').remove();
                var website_id = $('html').attr('data-website-id');
                var ga_key = wizardA.find('.o_ga_key').val();
                var view_id = wizardA.find('.o_view_id').val();
                var client_id = wizardA.find('.o_client_id').val();
                var client_secret = wizardA.find('.o_client_secret').val();
                if(ga_key.length == 0 || view_id.length == 0 || client_id.length == 0 || client_secret.length == 0){
                    wizardA.find(".o_configure_ab").after("<p class='o_message' style='color : red'> *"+_t("You must fill all the fields.")+"</p>");
                }
                else{
                    ajax.jsonRpc( '/website_version/set_google_access', 'call', {'ga_key':ga_key, 'view_id':view_id, 'client_id':client_id, 'client_secret':client_secret}).then(function (result) {
                        var context = base.get_context();
                        ajax.jsonRpc( '/website_version/google_access', 'call', {
                            fromurl: window.location.href,
                            local_context: context
                        }).done(function(o) {
                            if (o.status === "need_auth") {
                                var wizardC = $(qweb.render("website_version.message",{message:_t("You will be redirected to Google to authorize access to your Analytics Account!")}));
                                wizardC.appendTo($('body')).modal({"keyboard" :true});
                                wizardC.on('click','.o_confirm', function(){
                                    window.location.href = o.url;
                                });
                                wizardC.on('hidden.bs.modal', function () {$(this).remove();});
                            }
                            else if (o.status === "need_config_from_admin"){
                              if (confirm(_t("The Google Management API key needs to be configured before you can use it, do you want to do it now?"))) {
                                  window.location.href = o.action;
                              }
                            }
                        }).always(function() { $('button.GoogleAccess').prop('disabled', false); });
                    });
                }
            });
            wizardA.on('click','.o_validate_2', function(){
                var website_id = $('html').attr('data-website-id');
                var ga_key = wizardA.find('.o_ga_key').val();
                var view_id = wizardA.find('.o_view_id').val();
                if(ga_key.length == 0 || view_id.length == 0){
                    wizardA.find(".o_configure_ab").after("<p class='o_message' style='color : red'> *"+_t("You must fill all the fields.")+"</p>");
                }
                else{
                    ajax.jsonRpc( '/website_version/set_google_access', 'call', {'ga_key':ga_key, 'view_id':view_id, 'client_id':0, 'client_secret':0});
                }
            });
            wizardA.on('hidden.bs.modal', function () {$(this).remove();});
        });
    },

    manage_experiment: function() {
        window.location.href = '/web#return_label=Website&action=website_version.action_experiment';
    },

    statistics: function() {
        window.open('https://www.google.com/analytics/web/?authuser=0#report/siteopt-experiments/','_blank');
    }
    
});

$(document).ready(function() {
    var version = new EditorVersion();
    version.setElement($("#version-menu"));
    version.start();
});

return EditorVersion;

});
