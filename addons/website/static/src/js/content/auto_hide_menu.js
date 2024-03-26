/** @odoo-module **/

import { initAutoMoreMenu } from '@web/legacy/js/core/menu';

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 */
document.addEventListener('DOMContentLoaded', async () => {
    const header = document.querySelector('header#top');
    if (header) {
        const topMenu = header.querySelector('#top_menu');
        if (header.classList.contains('o_no_autohide_menu')) {
            topMenu.classList.remove('o_menu_loading');
            return;
        }
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
        initAutoMoreMenu(topMenu, {
            unfoldable: unfoldable,
            images: images,
            loadingStyleClasses: ['o_menu_loading'],
            // The "auto-hide" menu is closed when clicking inside the extra
            // menu items. The goal here is to prevent this default behaviour
            // on "edit" mode to allow correct editing of extra menu items, mega
            // menu content...
            autoClose: () => !document.body.classList.contains("editor_enable"),
        });
    }
});
