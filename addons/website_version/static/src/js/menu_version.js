(function() {
    'use strict';
    var _t = openerp._t;
    
    var website=openerp.website;
    var QWeb = openerp.qweb;
    website.add_template_file('/website_version/static/src/xml/all_versions.xml');
    website.add_template_file('/website_version/static/src/xml/publish.xml');
    
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

                    // openerp.jsonRpc( '/website_version/is_master', 'call', { 'view_id': view_id })
                    //     .then(function (result) {
                    //         self.$el.find(".publish").remove();
                    //         self.$el.find(".second_divider").remove();
                    //         if(!result){
                    //             self.$el.find(".publish_version").before('<li class="divider second_divider"> </li>');
                    //             self.$el.find(".publish_version").before('<li class="publish"><a href="#" data-action="publish" data-view_id='+view_id+'>Publish this page</a></li>');
                                
                    //         }
                    //     });

                });
                
            });
            return this._super();
        },
        
        create_snapshot: function() {
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
                openerp.jsonRpc( '/website_version/create_snapshot', 'call', { 'name': name }).then(function (result) {

                    location.reload();
                    alert("You are actually working on "+name+ " version.");
                }).fail(function(){
                    alert("This name already exists.");
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
            var snapshot_id = $(event.currentTarget).parent().data("snapshot_id");
            console.log(snapshot_id);
            openerp.jsonRpc( '/website_version/check_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    if (result){
                        if (confirm('Are you sure you want to delete a version which is in a running experiment?')){
                            openerp.jsonRpc( '/website_version/delete_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                                location.reload();
                            });
                        }
                    }
                    else{
                        openerp.jsonRpc( '/website_version/delete_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                            location.reload();
                        });
                    }
                });
        },

        publish: function(event) {
            var view_id = $(event.currentTarget).data("view_id");
            openerp.jsonRpc( '/website_version/publish', 'call', { 'view_id':view_id }).then(function (result) {
                    location.reload();
                });
        },

        publish_version: function(event) {
            var snapshot_id = $(event.currentTarget).data("snapshot_id");
            openerp.jsonRpc( '/website_version/publish_version', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    location.reload();
                });
        },

        google_analytics: function(event){
            window.location.href = 'https://www.google.com/analytics/web';

        },

        create_experiment: function() {
            var self = this;
            var view_id = $('html').attr('data-view-xmlid');
            openerp.jsonRpc( '/website_version/all_snapshots_all_goals', 'call', { 'view_id': view_id }).then(function (result) {
                self.wizard = $(openerp.qweb.render("website_version.create_experiment",{snapshots:result.tab_snap, goals:result.tab_goal}));
                self.wizard.appendTo($('body')).modal({"keyboard" :true});
                self.wizard.on('click','.create', function(){
                    var name = $('.name').val();
                    var tab = self.wizard.find('.form-field-required');
                    var result = [];
                    var i;
                    for (i = 0; i < tab.length; i++) {
                        if ($(tab[i]).is(':checked')) {
                            result.push($(tab[i]).attr('data-version_id'))
                        }
                    }
                    var objectives = self.wizard.find('.selectpicker').val();
                    var check = true;
                    if (name ==''){
                        alert("You must give a name to your experiment.");
                        check = false;
                    }
                    if (result.length == 0 && check){
                        alert("You must choose at least one version in your experiment.");
                        check = false;
                    }
                    console.log(name);
                    console.log(result);
                    console.log(objectives);
                    if(check){
                        openerp.jsonRpc( '/website_version/create_experiment', 'call', { 'name':name, 'snapshot_ids':result, 'objectives':objectives }).then(function (result) {
                            alert("Your experiment " + name + " is created. Now you can manage this experiment by clicking on Manage your experiments.");
                            location.reload();
                        });
                    } 
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
