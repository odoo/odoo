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

                    openerp.jsonRpc( '/website_version/is_master', 'call', { 'view_id': view_id })
                        .then(function (result) {
                            self.$el.find(".publish").remove();
                            self.$el.find(".second_divider").remove();
                            if(!result){
                                self.$el.find(".publish_version").before('<li class="divider second_divider"> </li>');
                                self.$el.find(".publish_version").before('<li class="publish"><a href="#" data-action="publish" data-view_id='+view_id+'>Publish this page</a></li>');
                                
                            }
                        });

                });
                
            });
            return this._super();
        },
        
        create_snapshot: function() {
            var m_names = new Array("January", "February", "March", 
                "April", "May", "June", "July", "August", "September", 
                "October", "November", "December");
            var d = new Date();
            var curr_date = d.getDate();
            var curr_month = d.getMonth();
            var curr_year = d.getFullYear();
            website.prompt({
                id: "editor_new_version",
                window_title: _t("New version"),
                input: "Version name" ,
                default :(curr_date + "-" + m_names[curr_month] + "-" + curr_year),
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
            openerp.jsonRpc( '/website_version/delete_snapshot', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                    location.reload();
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
        
    });

    
    $(document).ready(function() {
        var version = new website.EditorVersion();
        version.setElement($("#version-menu"));
        version.start();
    });
    
})();
