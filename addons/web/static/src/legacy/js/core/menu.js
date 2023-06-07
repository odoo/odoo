/** @odoo-module **/

const BREAKPOINT_SIZES = {sm: '575', md: '767', lg: '991', xl: '1199', xxl: '1399'};

/**
 * Creates an automatic 'more' dropdown-menu for a set of navbar items.
 *
 * @param {HTMLElement} el
 * @param {Object} [options]
 * @param {string} [options.unfoldable='none'] selector for items that do not
 * need to be added to dropdown-menu.
 * @param {float} [options.maxWidth] The max width value that menu content
 * can take => the overflowing (foldable) items are added in the dropdown-menu.
 * @param {string} [options.minSize] the menu auto-hide option will be disabled
 * if viewport is smaller than minSize.
 * @param {Array} [options.images=[]] images to wait for before menu update.
 * @param {Array} [options.loadingStyleClasses=[]] list of CSS classes to add while
 * updating the menu.
*/
export async function initAutoMoreMenu(el, options) {
    if (!el) {
        return;
    }
    const navbar = el.closest('.navbar');
    // Get breakpoint related information from the navbar to correctly handle
    // the "auto-hide" on mobile menu.
    const [breakpoint = 'md'] = navbar ? Object.keys(BREAKPOINT_SIZES)
        .filter(suffix => navbar.classList.contains(`navbar-expand-${suffix}`)) : [];
    const isNoHamburgerMenu = !!navbar && navbar.classList.contains('navbar-expand');

    options = Object.assign({
        unfoldable: 'none',
        maxWidth: false,
        // We cannot use `--breakpoint-xx` properties to get values with BS5.
        minSize: BREAKPOINT_SIZES[breakpoint],
        images: [],
        loadingStyleClasses: [],
    }, options || {});

    const isUserNavbar = el.parentElement.classList.contains('o_main_navbar');
    const dropdownSubMenuClasses = ['show', 'border-0', 'position-static'];
    const dropdownToggleClasses = ['h-auto', 'py-2', 'text-secondary'];
    const autoMarginLeftRegex = /\bm[sx]?(?:-(?:sm|md|lg|xl|xxl))?-auto\b/; // grep: ms-auto mx-auto
    const autoMarginRightRegex = /\bm[ex]?(?:-(?:sm|md|lg|xl|xxl))?-auto\b/; // grep: me-auto mx-auto
    var extraItemsToggle = null;
    let debounce;
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

    const debouncedAdapt = () => {
        clearTimeout(debounce);
        debounce = setTimeout(_adapt, 250);
    };
    window.addEventListener('resize', debouncedAdapt);

    el.addEventListener('dom:autoMoreMenu:adapt', _adapt);
    el.addEventListener('dom:autoMoreMenu:destroy', destroy, {once: true});

    function _restore() {
        if (!extraItemsToggle) {
            return;
        }
        // Move extra menu items from dropdown-menu to menu element in the same order.
        [...extraItemsToggle.querySelector('.dropdown-menu').children].forEach((item) => {
            if (!isUserNavbar) {
                item.classList.add('nav-item');
                const itemLink = item.querySelector('.dropdown-item');
                itemLink.classList.remove('dropdown-item');
                itemLink.classList.add('nav-link');
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
        if (options.loadingStyleClasses.length) {
            el.classList.add(...options.loadingStyleClasses);
        }
        _restore();

        // Ignore invisible/toggleable top menu element & small viewports.
        if (!el.getClientRects().length || el.closest('.show')
            || (window.matchMedia(`(max-width: ${options.minSize}px)`).matches && !isNoHamburgerMenu)) {
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

        if (options.maxWidth) {
            maxWidth = options.maxWidth();
        }
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
                navLink.classList.remove('nav-link');
                navLink.classList.add('dropdown-item');
                navLink.classList.toggle('active', el.classList.contains('active'));
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
        extraItemsToggleIcon.className = 'fa fa-plus';
        Object.entries({
            role: 'button',
            href: '#',
            class: 'nav-link dropdown-toggle o-no-caret',
            'data-bs-toggle': 'dropdown',
            'aria-expanded': false,
        }).forEach(([key, value]) => {
            extraItemsToggleLink.setAttribute(key, value);
        });

        extraItemsToggleLink.appendChild(extraItemsToggleIcon);
        extraItemsToggle.appendChild(extraItemsToggleLink);
        extraItemsToggle.appendChild(dropdownMenu);
        el.insertBefore(extraItemsToggle, target);
        return dropdownMenu;
    }

    function destroy() {
        _restore();
        window.removeEventListener('resize', debouncedAdapt);
        el.removeEventListener('dom:autoMoreMenu:adapt', _adapt);
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

    function _endAutoMoreMenu() {
        el.classList.remove(...options.loadingStyleClasses);
    }
}

/**
 * Cleans what has been done by ``initAutoMoreMenu``.
 *
 * @param {HTMLElement} el
 */
export function destroyAutoMoreMenu(el) {
    el.dispatchEvent(new Event('dom:autoMoreMenu:destroy'));
}
