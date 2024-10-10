/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.MegaMenuImagesSubtitles = publicWidget.Widget.extend({
    selector: ".s_mega_menu_images_subtitles",

    /**
     * @override
     */
    start() {
        // TODO: remove in master
        const links = this.el.querySelectorAll("nav a > div");
        for (const link of links) {
            link.classList.add("align-items-start");
        }

        return this._super(...arguments);
    },
});

export default publicWidget.registry.MegaMenuImagesSubtitles;
