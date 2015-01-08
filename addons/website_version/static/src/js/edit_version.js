(function() {
    'use strict';
    var hash = "#advanced-view-editor";
    var _t = openerp._t;
    
    var website=openerp.website;

    website.action= {};
    
    website.EditorBar.include({
        start: function() {
            var self = this;
            this.$el.on('click', '#save_as_new_version', function() {
                
                website.prompt({
                    id: "editor_new_version",
                    window_title: _t("New version"),
                    input: "Version name" ,
                    default :(moment().format('L')),
                }).then(function (name) {
                    var context = website.get_context();
                    openerp.jsonRpc( '/website_version/create_version', 'call', { 'name': name, 'version_id': 0 }).then(function (result) {
                        $('html').data('version_id', result);
                        
                        var wizard = $(openerp.qweb.render("website_version.message",{message:_.str.sprintf("You are actually working on %s version.", name)}));
                        wizard.appendTo($('body')).modal({"keyboard" :true});
                        wizard.on('click','.o_confirm', function(){
                            self.save();
                        });
                        wizard.on('hidden.bs.modal', function () {$(this).remove();});
                    }).fail(function(){
                        var wizard = $(openerp.qweb.render("website_version.message",{message:_t("This name already exists.")}));
                        wizard.appendTo($('body')).modal({"keyboard" :true});
                        wizard.on('hidden.bs.modal', function () {$(this).remove();});
                    });

                });
            
            });
            this.$el.on('click', '#save_and_publish', function() {
                var version_id = parseInt($('html').data('version_id'));
                if(version_id)
                {
                    self.save();
                }
                else
                {
                    var wizard = $(openerp.qweb.render("website_version.delete_message",{message:_t("Are you sure you want to publish your modifications.")}));
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
                    self.$el.find(".o_first_choice").before(openerp.qweb.render("all_options", {version:'Save on '+name}));
                }
                else{
                    self.$el.find(".o_first_choice").before(openerp.qweb.render("all_options", {version:'Save and Publish'}));
                }

            });
            
            return this._super();
        }
    });

    
})();