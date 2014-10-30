(function() {
    'use strict';
    var hash = "#advanced-view-editor";
    var _t = openerp._t;
    
    var website=openerp.website;

    website.action= {};
    
    website.EditorBar.include({
        start: function() {
            var self = this;
            $('#save_as_new_version').click(function() {
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
                    openerp.jsonRpc( '/website_version/create_snapshot', 'call', { 'name': name, 'snapshot_id': 0 }).then(function (result) {
                        $('html').data('snapshot_id', result);
                        
                        self.wizard = $(openerp.qweb.render("website_version.message",{message:"You are actually working on "+name+ " version."}));
                        self.wizard.appendTo($('body')).modal({"keyboard" :true});
                        self.wizard.on('click','.confirm', function(){
                            self.save();
                            location.reload();
                        });
                    }).fail(function(){
                        self.wizard = $(openerp.qweb.render("website_version.message",{message:"This name already exists."}));
                        self.wizard.appendTo($('body')).modal({"keyboard" :true});
                    });
                });
            
            });
            $('#save_and_publish').click(function() {
                var snapshot_id = $('html').data('snapshot_id');
                if(snapshot_id)
                {
                    var aManualDeferred = $.Deferred();
                    aManualDeferred.then(function () {
                        self.saveB();
                    })
                    .then(function () {
                        self.wizard = $(openerp.qweb.render("website_version.delete_message",{message:"Are you sure you want to publish this version."}));
                        self.wizard.appendTo($('body')).modal({"keyboard" :true});
                        self.wizard.on('click','.confirm', function(){
                            openerp.jsonRpc( '/website_version/publish_version', 'call', { 'snapshot_id':snapshot_id }).then(function (result) {
                                self.wizard = $(openerp.qweb.render("website_version.message",{message:"The version "+result+" has been saved and published."}));
                                self.wizard.appendTo($('body')).modal({"keyboard" :true});
                                self.wizard.on('click','.confirm', function(){
                                    location.reload();
                                });
                            });
                        });
                        self.wizard.on('click','.cancel', function(){
                            location.reload();
                        });
                    });
                    aManualDeferred.resolve();
                }
                else
                {
                    self.save();
                }

            });
            
            return this._super();
        }

    });

    website.EditorBarContent.include({
        start: function() {
            
            return this._super();
        },

        ab_testing: function() {
            window.location.href = '/web#return_label=Website&action=website_version.action_experiment';
        }
    });

    website.EditorBarCustomize.include({
        start: function() {
            return this._super();
        },
        load_menu: function () {
            var self = this;
            if(this.loaded) {
                return;
            }
            openerp.jsonRpc('/website_version/customize_template_get', 'call', { 'xml_id': this.view_name }).then(
                function(result) {
                    _.each(result, function (item) {
                        if (item.xml_id === "website.debugger" && !window.location.search.match(/[&?]debug(&|$)/)) return;
                        if (item.header) {
                            self.$menu.append('<li class="dropdown-header">' + item.name + '</li>');
                        } else {
                            self.$menu.append(_.str.sprintf('<li role="presentation"><a href="#" data-view-id="%s" role="menuitem"><strong class="fa fa%s-square-o"></strong> %s</a></li>',
                                item.id, item.active ? '-check' : '', item.name));
                        }
                    });
                    self.loaded = true;
                }
            );
        }
    });

    
})();