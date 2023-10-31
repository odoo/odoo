/** @odoo-module */

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('website_media_dialog_undraw', {
    test: true,
    url: '/',
}, [
{
    trigger: 'a[data-action=edit]',
},
wTourUtils.dragNDrop({
    id: 's_text_image',
    name: 'Text - Image',
}),
{
    trigger: '.s_text_image img',
    run: "dblclick",
},
{
    trigger: '.o_select_media_dialog:has(.o_we_search_select option[value="media-library"])',
},
]);
