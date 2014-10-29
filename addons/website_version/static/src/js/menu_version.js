(function() {
    'use strict';
    var _t = openerp._t;
    
    var website=openerp.website;
    var QWeb = openerp.qweb;
    website.add_template_file('/website_version/static/src/xml/all_versions.xml');
    
    website.EditorVersion = openerp.Widget.extend({
        start: function() {
            var self = this;

            $('html').data('snapshot_id', this.$el.find("#version-menu-button").data("snapshot_id"));
            var _get_context = website.get_context;
            website.get_context = function (dict) {
                return _.extend({ 'snapshot_id': $('html').data('snapshot_id') }, _get_context(dict));
            };

            self.$el.on('click', 'a[data-action]', function(ev) {
                ev.preventDefault();
                self[$(this).data('action')](ev);
            });

            this.$el.find('#version-menu-button').click(function() {
                var view_id = $('html').attr('data-view-xmlid');
                openerp.jsonRpc( '/website_version/all_snapshots', 'call', { 'view_id': view_id }).then(function (result) {
                    self.$el.find(".snapshot").remove();
                    self.$el.find(".first_divider").before(QWeb.render("all_versions", {snapshots:result}));

                });
                openerp.jsonRpc( '/website_version/has_experiments', 'call', { 'view_id': view_id }).then(function (result) {
                    self.$el.find(".experiment").remove();
                    if(result){
                        self.$el.find(".create_experiment").after(QWeb.render("experiment_menu"));
                    }
                });
                
            });
            return this._super();
        },
        
        duplicate_version: function(event) {
            var snapshot_id = $(event.currentTarget).parent().parent().parent().data("snapshot_id");
            console.log(snapshot_id);
            var m_names = new Array("jan", "feb", "mar",
                "apr", "may", "jun", "jul", "aug", "sep",
                "oct", "nov", "dec");
            var d = new Date();
            var curr_date = d.getDate();
            var curr_month = d.getMonth();
            var curr_year = d.getFullYear();
            website.prompt({
                id: "editor_new_version",
                window_title: _t("New version"),
                input: "Version name" ,
                default :(curr_date + " " + m_names[curr_month] + " " + curr_year),
            }).then(function (name) {
                var context = website.get_context();
                openerp.jsonRpc( '/website_version/create_snapshot', 'call', { 'name': name, 'snapshot_id': snapshot_id}).then(function (result) {

                    self.wizard = $(openerp.qweb.render("website_version.message",{message:"You are actually working on "+name+ " version."}));
                    self.wizard.appendTo($('body')).modal({"keyboard" :true});
                    self.wizard.on('click','.confirm', function(){
                        location.reload();
                    });
                }).fail(function(){
                    self.wizard = $(openerp.qweb.render("website_version.message",{message:"This name already exists."}));
                    self.wizard.appendTo($('body')).modal({"keyboard" :true});

                });
            });
        },
        
        change_snapshot: function(event) {
            var snapshot_id = $(event.target).parent().data("snapshot_id");
            openerp.jsonRpc( '/website_version/change_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    location.reload();
                });
        },

        master: function(event) {
            openerp.jsonRpc( '/website_version/master', 'call', {}).then(function (result) {
                    location.reload();
                });
        },

        delete_snapshot: function(event) {
            var snapshot_id = $(event.currentTarget).parent().parent().parent().data("snapshot_id");
            console.log(snapshot_id);
            openerp.jsonRpc( '/website_version/check_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    if (result){
                        self.wizard = $(openerp.qweb.render("website_version.message",{message:"You cannot delete this version because it is in a running experiment"}));
                        self.wizard.appendTo($('body')).modal({"keyboard" :true});
                    }
                    else{
                        self.wizard = $(openerp.qweb.render("website_version.delete_message",{message:"Are you sure you want to delete this version."}));
                        self.wizard.appendTo($('body')).modal({"keyboard" :true});
                        self.wizard.on('click','.confirm', function(){
                            openerp.jsonRpc( '/website_version/delete_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                                self.wizard = $(openerp.qweb.render("website_version.message",{message:"The version "+result+" has been deleted."}));
                                self.wizard.appendTo($('body')).modal({"keyboard" :true});
                                self.wizard.on('click','.confirm', function(){
                                    location.reload();
                                });
                            });
                        });
                    }
                });
        },

        publish_version: function(event) {
            var snapshot_id = $(event.currentTarget).parent().parent().parent().data("snapshot_id");
            console.log(snapshot_id);
            openerp.jsonRpc( '/website_version/publish_version', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    self.wizard = $(openerp.qweb.render("website_version.message",{message:"The version "+result+" has been published."}));
                    self.wizard.appendTo($('body')).modal({"keyboard" :true});
                    self.wizard.on('click','.confirm', function(){
                        location.reload();
                    });
                });
        },

        google_analytics: function(event){
            window.location.href = 'https://www.google.com/analytics/web';

        },

        create_experiment: function() {
            var self = this;
            var view_id = $('html').attr('data-view-xmlid');
            openerp.jsonRpc( '/website_version/all_snapshots_all_goals', 'call', { 'view_id': view_id }).then(function (result) {
                self.wizard = $(openerp.qweb.render("website_version.create_experiment",{snapshots:result.tab_snap, goals:result.tab_goal, config:result.check_conf}));
                self.wizard.appendTo($('body')).modal({"keyboard" :true});
                self.wizard.on('click','.draft', function(){
                    self.wizard.find('.message').remove();
                    var name = self.wizard.find('.name').val();
                    var tab = self.wizard.find('.version');
                    var result = [];
                    var i;
                    for (i = 0; i < tab.length; i++) {
                        if ($(tab[i]).is(':checked')) {
                            result.push($(tab[i]).attr('data-version_id'));
                        }
                    }
                    var objectives = self.wizard.find('.box').val();
                    var check = true;
                    if (name =='' || name == null){
                        self.wizard.find(".name").after("<p class='message' style='color : red'> *This field is required</p>");
                        check = false;
                    }
                    if (result.length == 0 && check){
                        self.wizard.find(".versions").after("<p class='message' style='color : red'> *You must select at least one version which is not the original</p>");
                        check = false;
                    }
                    if(check){
                        openerp.jsonRpc( '/website_version/create_experiment', 'call', { 'name':name, 'snapshot_ids':result, 'objectives':objectives }).then(function (result) {

                            self.wizard = $(openerp.qweb.render("website_version.message",{message:"Your experiment " + name + " is created. Now you can manage this experiment by clicking on Manage Experiments."}));
                            self.wizard.appendTo($('body')).modal({"keyboard" :true});
                            self.wizard.on('click','.confirm', function(){
                                location.reload();
                            });
                        });
                    }
                });
            
                self.wizard.on('click','.launch', function(){
                    self.wizard.find('.message').remove();
                    var name = $('.name').val();
                    var tab = self.wizard.find('.version');
                    var result = [];
                    var i;
                    for (i = 0; i < tab.length; i++) {
                        if ($(tab[i]).is(':checked')) {
                            result.push(parseInt($(tab[i]).attr('data-version_id')));
                        }
                    }
                    var objectives = self.wizard.find('.box').val();
                    var check = true;
                    if (name =='' || name == null){
                        self.wizard.find(".name").after("<p class='message' style='color : red'> *This field is required</p>");
                        check = false;
                    }
                    if (result.length == 0 && check){
                        self.wizard.find(".versions").after("<p class='message' style='color : red'> *You must select at least one version which is not the original</p>");
                        check = false;
                    }
                    if(check){
                        openerp.jsonRpc( '/website_version/launch_experiment', 'call', { 'name':name, 'snapshot_ids':result, 'objectives':objectives }).then(function (result) {
                            if (result){
                                self.wizard = $(openerp.qweb.render("website_version.message",{message:"Your experiment " + name + " is launched. Now you can check its statistics by clicking on Statistics."}));
                                self.wizard.appendTo($('body')).modal({"keyboard" :true});
                                self.wizard.on('click','.confirm', function(){
                                    location.reload();
                                });

                            }
                            else{
                                self.wizard.find(".versions").after("<p class='message' style='color : red'> *Your experiment " + name + " cannot be launched because this experiment contains a view which is already used in another running experiment. But you can create a draft of this experiment.</p>");
                            }
                        });
                    }
                });
                self.wizard.on('click','.configure', function(){
                    var website_id = $('html').attr('data-website-id');
                    window.location.href ='/web#id='+website_id+'&view_type=form&model=website&action=website_version.action_website_view';
                });
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
        var version = new website.EditorVersion();
        version.setElement($("#version-menu"));
        version.start();
    });
    
})();
