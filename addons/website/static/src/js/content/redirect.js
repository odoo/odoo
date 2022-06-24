/** @odoo-module */

import { session } from '@web/session';
// import { _t } from "@web/core/l10n/translation"; // FIXME don't know why it does not work
const _t = str => str;

/**
 * This script, served with frontend pages, displays buttons in the top left
 * corner to provide the authenticated user an access to his odoo backend.
 * In the case of the page being viewed in the website_preview client action,
 * it will forward some events to its parent.
 */
document.addEventListener('DOMContentLoaded', () => {
    if (session.is_website_user) {
        return;
    }

    const editInBackendUserDropdownLinkEl = document.getElementById('o_edit_in_backend_user_dropdown_link');

    if (!window.frameElement) {
        const websiteId = document.documentElement.dataset.websiteId;
        const {pathname, search} = window.location;
        const params = new URLSearchParams(search);
        const enableEditor = params.get('enable_editor');
        const editTranslations = params.get('edit_translations');
        params.delete('enable_editor');
        let newSearch = params.toString();
        if (newSearch) {
            newSearch = '?' + newSearch;
        }
        const backendPath = `/web#action=website.website_preview&path=${encodeURIComponent(`${pathname}${newSearch}`)}&website_id=${websiteId}`;

        const autoredirectToBackendAction = enableEditor || editTranslations;
        if (autoredirectToBackendAction) {
            document.body.innerHTML = '';
            if (enableEditor) {
                window.location.replace(`${backendPath}&enable_editor=1`);
            } else if (editTranslations) {
                window.location.replace(`${backendPath}&edit_translations=1`);
            } else {
                window.location.replace(backendPath);
            }
        } else {
            // FIXME this UI does not respect access rights yet but we will
            // probably end up doing it in XML instead of JS anyway.
            const frontendToBackendNavEl = document.createElement('div');
            frontendToBackendNavEl.classList.add('o_frontend_to_backend_nav');
            frontendToBackendNavEl.addEventListener('click', ev => {
                frontendToBackendNavEl.classList.add('o_frontend_to_backend_nav_opened');
                setTimeout(() => {
                    // TODO find a better way? Useful so that hover effects work
                    // after the opening.
                    frontendToBackendNavEl.classList.add('o_frontend_to_backend_nav_fully_opened');
                }, 600);
            }, { once: true });

            const loadingIconEl = document.createElement('i');
            loadingIconEl.classList.add('o_frontend_to_backend_icon', 'fa', 'fa-arrow-right');
            frontendToBackendNavEl.appendChild(loadingIconEl);

            const backendAppsButtonEl = document.createElement('a');
            backendAppsButtonEl.href = '/web';
            backendAppsButtonEl.title = _t("Go to your Odoo Apps");
            backendAppsButtonEl.classList.add('o_frontend_to_backend_apps_btn', 'fa', 'fa-th');
            frontendToBackendNavEl.appendChild(backendAppsButtonEl);

            const backendEditButtonEl = document.createElement('a');
            backendEditButtonEl.href = `${backendPath}&enable_editor=1`;
            backendEditButtonEl.textContent = _t("Edit");
            backendEditButtonEl.title = _t("Edit your page content");
            backendEditButtonEl.classList.add('o_frontend_to_backend_edit_btn');
            const backendEditButtonIconEl = document.createElement('i');
            backendEditButtonIconEl.classList.add('fa', 'fa-pencil');
            backendEditButtonEl.prepend(backendEditButtonIconEl);
            frontendToBackendNavEl.appendChild(backendEditButtonEl);

            if (editInBackendUserDropdownLinkEl) {
                editInBackendUserDropdownLinkEl.href = backendPath;
            }

            document.body.appendChild(frontendToBackendNavEl);
        }
    } else {
        const backendUserDropdownLinkEl = document.getElementById('o_backend_user_dropdown_link');
        if (backendUserDropdownLinkEl) {
            backendUserDropdownLinkEl.classList.add('d-none');
            backendUserDropdownLinkEl.classList.remove('d-flex');
        }
        if (editInBackendUserDropdownLinkEl) {
            editInBackendUserDropdownLinkEl.classList.add('d-none');
            editInBackendUserDropdownLinkEl.classList.remove('d-flex');
        }

        // Multiple reasons to do this:
        // - It seems like DOMContentLoaded doesn't always trigger when
        //   listened from the parent window
        // - Having an event that's fire only when the page is from Odoo avoids
        //   weird behaviours. (e.g. if we want to clear out the iframe, it might
        //   fire an DOMContentLoaded on a non odoo page)
        window.frameElement.dispatchEvent(new CustomEvent('OdooFrameContentLoaded'));
    }
});
