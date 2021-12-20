/** @odoo-module */
import { session } from '@web/session';

document.addEventListener('DOMContentLoaded', () => {
    const htmlEl = document.documentElement;
    if (!session.is_website_user && !window.frameElement) {
        const websiteId = htmlEl.dataset.websiteId;
        const {pathname, search} = window.location;
        const params = new URLSearchParams(search).toString();
        document.body.innerHTML = '';

        window.location.replace(`/web#action=website.website_editor&path=${encodeURIComponent(params ? `${pathname}?${params}` : pathname)}&website_id=${websiteId}`);
    }
});
