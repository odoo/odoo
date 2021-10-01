/** @odoo-module **/

import { initAutoMoreMenu } from '@web/legacy/js/core/menu';

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 */
document.addEventListener('DOMContentLoaded', async () => {
    const header = document.querySelector('header#top');
    if (!header || header.classList.contains('o_no_autohide_menu')) {
        return;
    }
    const topMenu = header.querySelector('#top_menu');
    const unfoldable = '.divider, .divider ~ li, .o_no_autohide_item, .js_language_selector';
    const excludedImagesSelector = '.o_mega_menu, .o_offcanvas_logo_container, .o_lang_flag';
    const excludedImages = [...header.querySelectorAll(excludedImagesSelector)];
    const images = [...header.querySelectorAll('img')].filter((img) => {
        excludedImages.forEach(node => {
            if (node.contains(img)) {
                return false;
            }
        });
        return img.matches && !img.matches(excludedImagesSelector);
    });
    const defs = images.map((image) => {
        if (image.complete) {
            return null;
        }
        return new Promise(function (resolve, reject) {
            image.addEventListener('load', () => {
                resolve();
            });
        });
    });

    await Promise.all(defs);
    initAutoMoreMenu(topMenu, {unfoldable: unfoldable});
    topMenu.classList.remove('o_menu_loading');
});
