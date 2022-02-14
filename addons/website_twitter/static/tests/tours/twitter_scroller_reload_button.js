odoo.define('website_twitter.tour.twitter_scroller_reload_button', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require('web_editor.base');

tour.register('twitter_scroller_reload_button', {
    test: true,
    url: '/?enable_editor=1',
    wait_for: base.ready(),
}, [{
    trigger: '#snippet_feature .oe_snippet:has(span:contains("Twitter Scroller")) .oe_snippet_thumbnail',
    content: 'Drag the Twitter Scroller snippet and drop it in your page.',
    run: 'drag_and_drop #wrap',
    }, {
    trigger: '#wrap .twitter',
    content: 'Activate the Twitter Scroller snippet editor.',
}, {
    trigger: '#wrap .twitter:has(.btn span:contains("Reload"))',
    content: 'Check if the reload button was added to the DOM.',
}, {
    trigger: '.oe_snippet_remove:last',
    content: 'Remove the twitter scroller snippet.',
},
{
    trigger: '#wrap:not(:has(.btn span:contains("Reload")))',
    content: 'Check if the reload button was removed from the DOM.',
}]);

});
