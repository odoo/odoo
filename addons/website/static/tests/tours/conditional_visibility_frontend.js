/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('conditional_visibility_2', {
    test: true,
    url: '/?utm_medium=Email',
},
[{
    content: 'The content previously hidden should now be visible',
    trigger: 'body #wrap',
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0].getElementsByClassName('s_text_image')[0]);
        if (style.display === 'none') {
            console.error('error This item should now be visible because utm_medium === email');
        }
    },
},
]);
