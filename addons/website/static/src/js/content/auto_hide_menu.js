/** @odoo-module **/

const BREAKPOINT_SIZES = {sm: '575', md: '767', lg: '991', xl: '1199', xxl: '1399'};

/**
 * Creates an automatic 'more' dropdown-menu for a set of navbar items.
 *
 * @param {HTMLElement} el
 * @param {Object} [options]
 * @param {string} [options.unfoldable='none'] selector for items that do not
 * need to be added to dropdown-menu.
 * @param {Array} [options.images=[]] images to wait for before menu update.
 * @param {Array} [options.loadingStyleClasses=[]] list of CSS classes to add while
 * updating the menu.
 * @param {function} [options.autoClose] returns a value that represents the
 * "auto-close" behaviour of the dropdown (e.g. used to prevent auto-closing in
 * "edit" mode).
*/
async function autoHideMenu(el, options) {
    if (!el) {
        return;
    }
    const navbar = el.closest('.navbar');
    // Get breakpoint related information from the navbar to correctly handle
    // the "auto-hide" on mobile menu.
    const [breakpoint = 'md'] = navbar ? Object.keys(BREAKPOINT_SIZES)
        .filter(suffix => navbar.classList.contains(`navbar-expand-${suffix}`)) : [];
    const isNoHamburgerMenu = !!navbar && navbar.classList.contains('navbar-expand');
    const minSize = BREAKPOINT_SIZES[breakpoint];
    let isExtraMenuOpen = false;

    options = Object.assign({
        unfoldable: 'none',
        images: [],
        loadingStyleClasses: [],
        autoClose: () => true,
    }, options || {});

    const isUserNavbar = el.parentElement.classList.contains('o_main_navbar');
    const dropdownSubMenuClasses = ['show', 'border-0', 'position-static'];
    const dropdownToggleClasses = ['h-auto', 'py-2', 'text-secondary'];
    const autoMarginLeftRegex = /\bm[sx]?(?:-(?:sm|md|lg|xl|xxl))?-auto\b/; // grep: ms-auto mx-auto
    const autoMarginRightRegex = /\bm[ex]?(?:-(?:sm|md|lg|xl|xxl))?-auto\b/; // grep: me-auto mx-auto
    var extraItemsToggle = null;
    const afterFontsloading = new Promise((resolve) => {
        if (document.fonts) {
            document.fonts.ready.then(resolve);
        } else {
            // IE: don't wait more than max .15s.
            setTimeout(resolve, 150);
        }
    });
    afterFontsloading.then(_adapt);

    if (options.images.length) {
        await _afterImagesLoading(options.images);
        _adapt();
    }

    let pending = false;
    let refreshId = null;
    const onRefresh = () => {
        if (pending) {
            refreshId = window.requestAnimationFrame(onRefresh);
            _adapt();
            pending = false;
        } else {
            refreshId = null;
        }
    };
    // This should throttle the `_adapt()` method to the browser's refresh
    // rate. The first menu adaptation is always executed immediately.
    const throttleAdapt = () => {
        if (refreshId === null) {
            refreshId = window.requestAnimationFrame(onRefresh);
            _adapt();
        } else {
            pending = true;
        }
    };

    window.addEventListener('resize', throttleAdapt);

    function _restore() {
        if (!extraItemsToggle) {
            return;
        }
        // Move extra menu items from dropdown-menu to menu element in the same order.
        [...extraItemsToggle.querySelector('.dropdown-menu').children].forEach((item) => {
            if (!isUserNavbar) {
                item.classList.add('nav-item');
                const itemLink = item.querySelector('.dropdown-item');
                if (itemLink) {
                    itemLink.classList.remove('dropdown-item');
                    itemLink.classList.add('nav-link');
                }
            } else {
                item.classList.remove('dropdown-item');
                const dropdownSubMenu = item.querySelector('.dropdown-menu');
                const dropdownSubMenuButton = item.querySelector('.dropdown-toggle');
                if (dropdownSubMenu) {
                    dropdownSubMenu.classList.remove(...dropdownSubMenuClasses);
                }
                if (dropdownSubMenuButton) {
                    dropdownSubMenuButton.classList.remove(...dropdownToggleClasses);
                }
            }
            el.insertBefore(item, extraItemsToggle);
        });
        extraItemsToggle.remove();
        extraItemsToggle = null;
    }

    function _adapt() {
        const wysiwyg = window.$ && $('#wrapwrap').data('wysiwyg');
        const odooEditor = wysiwyg && wysiwyg.odooEditor;
        if (odooEditor) {
            odooEditor.observerUnactive("adapt");
            odooEditor.withoutRollback(__adapt);
            odooEditor.observerActive("adapt");
            return;
        }
        __adapt();
    }

    function __adapt() {
        if (options.loadingStyleClasses.length) {
            el.classList.add(...options.loadingStyleClasses);
        }
        // The goal here is to get the state of the extra menu dropdown if it is
        // there, which will be restored after the menu adaptation.
        const extraMenuEl = _getExtraMenuEl();
        isExtraMenuOpen = extraMenuEl && extraMenuEl.classList.contains("show");
        _restore();

        // Ignore invisible/toggleable top menu element & small viewports.
        if (!el.getClientRects().length || el.closest('.show')
            || (window.matchMedia(`(max-width: ${minSize}px)`).matches && !isNoHamburgerMenu)) {
            return _endAutoMoreMenu();
        }

        let unfoldableItems = [];
        const items = [...el.children].filter((node) => {
            if (node.matches && !node.matches(options.unfoldable)) {
                return true;
            }
            unfoldableItems.push(node);
            return false;
        });
        var nbItems = items.length;
        var menuItemsWidth = items.reduce((sum, el) => sum + computeFloatOuterWidthWithMargins(el, true, true, false), 0);
        let maxWidth = 0;

        if (!maxWidth) {
            maxWidth = computeFloatOuterWidthWithMargins(el, true, true, true);
            var style = window.getComputedStyle(el);
            maxWidth -= (parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth));
            maxWidth -= unfoldableItems.reduce((sum, el) => sum + computeFloatOuterWidthWithMargins(el, true, true, false), 0);
        }
        // Ignore if there is no overflow.
        if (maxWidth - menuItemsWidth >= -0.001) {
            return _endAutoMoreMenu();
        }

        const dropdownMenu = _addExtraItemsButton(items[nbItems - 1].nextElementSibling);
        menuItemsWidth += computeFloatOuterWidthWithMargins(extraItemsToggle, true, true, false);
        do {
            menuItemsWidth -= computeFloatOuterWidthWithMargins(items[--nbItems], true, true, false);
        } while (!(maxWidth - menuItemsWidth >= -0.001) && (nbItems > 0));

        const extraItems = items.slice(nbItems);
        extraItems.forEach((el) => {
            if (!isUserNavbar) {
                const navLink = el.querySelector('.nav-link, a');
                el.classList.remove('nav-item');
                if (navLink) {
                    navLink.classList.remove('nav-link');
                    navLink.classList.add('dropdown-item');
                    navLink.classList.toggle('active', el.classList.contains('active'));
                }
            } else {
                const dropdownSubMenu = el.querySelector('.dropdown-menu');
                const dropdownSubMenuButton = el.querySelector('.dropdown-toggle');
                el.classList.add('dropdown-item', 'p-0');
                if (dropdownSubMenu) {
                    dropdownSubMenu.classList.add(...dropdownSubMenuClasses);
                }
                if (dropdownSubMenuButton) {
                    dropdownSubMenuButton.classList.add(...dropdownToggleClasses);
                }
            }
            dropdownMenu.appendChild(el);
        });
        _endAutoMoreMenu();
    }

    function computeFloatOuterWidthWithMargins(el, mLeft, mRight, considerAutoMargins) {
        var rect = el.getBoundingClientRect();
        var style = window.getComputedStyle(el);
        var outerWidth = rect.right - rect.left;
        const isRTL = style.direction === 'rtl';
        if (mLeft !== false && (considerAutoMargins || !(isRTL ? autoMarginRightRegex : autoMarginLeftRegex).test(el.getAttribute('class')))) {
            outerWidth += parseFloat(style.marginLeft);
        }
        if (mRight !== false && (considerAutoMargins || !(isRTL ? autoMarginLeftRegex : autoMarginRightRegex).test(el.getAttribute('class')))) {
            outerWidth += parseFloat(style.marginRight);
        }
        // Would be NaN for invisible elements for example
        return isNaN(outerWidth) ? 0 : outerWidth;
    }

    function _addExtraItemsButton(target) {
        let dropdownMenu = document.createElement('div');
        extraItemsToggle = dropdownMenu.cloneNode();
        const extraItemsToggleIcon = document.createElement('i');
        const extraItemsToggleLink = document.createElement('a');

        dropdownMenu.className = 'dropdown-menu';
        extraItemsToggle.className = 'nav-item dropdown o_extra_menu_items';
        extraItemsToggle.setAttribute("role", "presentation");
        extraItemsToggleIcon.className = 'fa fa-plus';
        const extraItemsToggleAriaLabel = el.closest("[data-extra-items-toggle-aria-label]")
            ?.dataset.extraItemsToggleAriaLabel;
        Object.entries({
            role: 'menuitem',
            href: '#',
            class: 'nav-link dropdown-toggle o-no-caret',
            'data-bs-toggle': 'dropdown',
            'aria-expanded': false,
            'aria-label': extraItemsToggleAriaLabel || " ",
        }).forEach(([key, value]) => {
            extraItemsToggleLink.setAttribute(key, value);
        });

        extraItemsToggleLink.appendChild(extraItemsToggleIcon);
        extraItemsToggle.appendChild(extraItemsToggleLink);
        extraItemsToggle.appendChild(dropdownMenu);
        el.insertBefore(extraItemsToggle, target);
        if (!options.autoClose()) {
            extraItemsToggleLink.setAttribute("data-bs-auto-close", "outside");
        }
        return dropdownMenu;
    }

    function _afterImagesLoading(images) {
        const defs = images.map((image) => {
            if (image.complete || !image.getClientRects().length) {
                return null;
            }
            return new Promise(function (resolve, reject) {
                if (!image.width) {
                    // The purpose of the 'o_menu_image_placeholder' class is to add a default
                    // size to non loaded images (on the first update) to prevent flickering.
                    image.classList.add('o_menu_image_placeholder');
                }
                image.addEventListener('load', () => {
                    image.classList.remove('o_menu_image_placeholder');
                    resolve();
                });
            });
        });
        return Promise.all(defs);
    }

    function _getExtraMenuEl() {
        return el.querySelector(".o_extra_menu_items .dropdown-toggle");
    }

    function _endAutoMoreMenu() {
        const extraMenuEl = _getExtraMenuEl();
        if (extraMenuEl && isExtraMenuOpen) {
            extraMenuEl.click();
        }
        el.classList.remove(...options.loadingStyleClasses);
    }
}

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 */
document.addEventListener('DOMContentLoaded', async () => {
    const header = document.querySelector('header#top');
    if (header) {
        // TODO in master: remove `#top_menu` from the selector.
        const topMenu = header.querySelector("#top_menu, .top_menu");
        const unfoldable = ".divider, .divider ~ li, .o_no_autohide_item, .js_language_selector";
        if (!topMenu.querySelector(`:scope > :not(${unfoldable})`)
                || header.classList.contains("o_no_autohide_menu")) {
            topMenu.classList.remove('o_menu_loading');
            return;
        }
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
        autoHideMenu(topMenu, {
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
