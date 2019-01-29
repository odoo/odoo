odoo.define('wslides.tour_slides', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('tour_slides', {
    test: true,
    url: '/slides',
}, [{
    content: 'Click on "+ New"',
    trigger: 'li.o_new_content_menu a',
    run: 'click',
}, {
	content: 'Click on "New Slide"',
    trigger: 'a[data-action="new_slide"]',
    run: 'click',
}, {
	content: 'Choose second channel',
    trigger: 'select[id="slide_channel_id"]',
    run: function () {
		this.$anchor.val(this.$anchor.find('option')[1].value);
    }
}, {
	content: 'Click on "Select"',
    trigger: 'button.btn-primary',
    run: 'click',
}
]);

});
