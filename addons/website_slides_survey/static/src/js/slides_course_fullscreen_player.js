odoo.define('website_slides_survey.fullscreen', function (require) {
    "use strict";
    
    var core = require('web.core');
    var _t = core._t;
    var Fullscreen = require('website_slides.fullscreen');
    
    Fullscreen.include({
        xmlDependencies: (Fullscreen.prototype.xmlDependencies || []).concat(
            ["/website_slides_survey/static/src/xml/website_slides_fullscreen.xml"]
        ),
    });
    
    });
    