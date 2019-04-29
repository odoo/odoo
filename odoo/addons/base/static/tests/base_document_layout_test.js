odoo.define('base.tour_test_base_document_layout', function (require) {
    'use strict';
    
    var tour = require('web_tour.tour');
    
    tour.register('test_base_document_layout', {
        test: true,
        url: '/web#id=&action=91&model=res.config.settings&view_type=form&menu_id=4',
    }, [
        {
            content: 'Click on "Configure Document Layout"',
            trigger: 'a.btn:contains("Configure Document Layout")',
            //run: "ABCD" || function() {foobar();}
        },
    ]);
});
