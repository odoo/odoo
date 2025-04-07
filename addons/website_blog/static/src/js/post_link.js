/** @odoo-module **/

import publicWidget from 'web.public.widget';
import postLink from 'website.post_link';

// TODO: remove in master
publicWidget.registry.blog_post_link = postLink.extend({
    selector: "select[name='archive'], span:has(.fa-calendar-o) a",
});
