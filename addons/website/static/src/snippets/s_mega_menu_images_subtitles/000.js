/** @odoo-module **/

/** 
 * TODO: remove this file in master.
 * This file provides a PublicWidget to address the issue of image distortion
 * in the Mega Menu using "Images Subtitles" template 
 * for the stable version
*/

import publicWidget from 'web.public.widget';

publicWidget.registry.MegaMenuImagesSubtitles = publicWidget.Widget.extend({
    selector: ".s_mega_menu_images_subtitles",

    /**
     * @override
     */
    start() {
        const links = this.el.querySelectorAll("nav a > div");
        for (const link of links) {
            link.classList.add("align-items-start");
        }
        return this._super(...arguments);
    },
});

export default publicWidget.registry.MegaMenuImagesSubtitles;
