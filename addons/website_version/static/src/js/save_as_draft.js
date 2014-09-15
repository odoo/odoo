(function() {
    'use strict';
    var hash = "#advanced-view-editor";
    var _t = openerp._t;
    
    var website=openerp.website;

    website.action= {};
    
    website.EditorBar.include({
        start: function() {
            var self = this;
            $('#master_edit_button').click(function() {
                console.log("You just clicked!");
                
                website.prompt({
                    id: "editor_new_snapshot",
                    window_title: _t("New snapshot"),
                    input: "Snapshot name" ,
                    default :(new Date()),
                }).then(function (name) {
                    var context = website.get_context();
                    openerp.jsonRpc( '/website_version/create_snapshot', 'call', { 'name': name }).then(function (result) {
                        context = website.get_context();
                        self.save();
                        location.reload();
                    }).fail(function(){
                        alert("This name already exists.");
                    });
                });
            
            });
            return this._super();
        }
    });
    
    website.ready().done(function() {
        console.log("This is the solution!");
    });
    
})();