project_timesheet = _.clone(openerp);;
(function() {
'use strict';

    //openerp.project_timesheet = project_timesheet;

    //project_timesheet.qweb = new QWeb2.Engine();
    odoo_project_timesheet_db(project_timesheet); //Import db.js
    odoo_project_timesheet_models(project_timesheet); //Import model.js
    odoo_project_timesheet_screens(project_timesheet); // Import screens.js
    odoo_project_timesheet_widgets(project_timesheet); //Import widget.js

    project_timesheet.App = (function() {
    
        function App($element) {
            this.initialize($element);
        }
        var templates_def = $.Deferred().resolve();
        App.prototype.add_template_file = function(template) {
            var def = $.Deferred();
            templates_def = templates_def.then(function() {
                openerp.qweb.add_template(template, function(err) {
                    if (err) {
                        def.reject(err);
                    } else {
                        def.resolve();
                    }
                });
                return def;
            });
            return def;
        };
        App.prototype.initialize = function($element) {
            this.$el = $element;
    
            var Connect = new XMLHttpRequest();
            // Define which file to open and
            // send the request.
            Connect.open("GET", "static/src/xml/project_timesheet.xml", false);
            Connect.setRequestHeader("Content-Type", "text/xml");
            Connect.send(null);
     
            // Place the response in an XML document.
            var xml = Connect.responseXML;
    
            //project_timesheet.qweb.add_template(xml);
            this.add_template_file(xml);
            this.pt_widget = new project_timesheet.project_timesheet_widget(null, {});
            this.pt_widget.appendTo($element);
        };
        return App;
    })();

    jQuery(document).ready(function() {
        //var project_timesheet = {};
        var app = new project_timesheet.App($(".odoo_project_timesheet"));
    });
})();