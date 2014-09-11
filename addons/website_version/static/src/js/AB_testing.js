(function() {
    'use strict';
    var _t = openerp._t;
    var website=openerp.website;


    
    website.EditorBarContent.include({
        start: function() {
            return this._super();
        },
    });
    
    $(document).ready(function() {
        console.log($('html').attr('data-view-xmlid'));
    });
    
})();