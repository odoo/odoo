website_forum_chrome = _.clone(openerp);
(function() {
    'use strict';

    odoo_website_forum_chrome_widget(website_forum_chrome); //Import widget.js

    website_forum_chrome.App = (function() {
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
            Connect.open("GET", "static/src/xml/website_forum_chrome.xml", false);
            Connect.setRequestHeader("Content-Type", "text/xml");
            Connect.send(null);

            // Place the response in an XML document.
            var xml = Connect.responseXML;

            this.add_template_file(xml);
           this.website_forum_widget = new website_forum_chrome.website_forum_chrome_widget(null, {});
           this.website_forum_widget.appendTo($element);
        };
        return App;
    })();

    jQuery(document).ready(function() {
        var app = new website_forum_chrome.App($(".odoo_website_forum_chrome"));
    });
})();