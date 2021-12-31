/** @odoo-module */
import { session } from '@web/session';

document.addEventListener('DOMContentLoaded', () => {
    if (session.is_website_user) {
        return;
    }

    if (!window.frameElement) {
        const websiteId = document.documentElement.dataset.websiteId;
        const {pathname, search} = window.location;
        const params = new URLSearchParams(search).toString();
        document.body.innerHTML = '';

        window.location.replace(`/web#action=website.website_editor&path=${encodeURIComponent(params ? `${pathname}?${params}` : pathname)}&website_id=${websiteId}`);
    } else {
        document.addEventListener('click', (ev) => {
            const isEditorEnabled = document.body.classList.contains('editor_enable');
            const linkEl = ev.target.closest('[href]');
            if (!linkEl) {
                return;
            }

            const {href, host, target, pathname} = linkEl;
            const isNewWindow = target === '_blank';
            const isInIframe = host === window.location.host && !pathname.startsWith('/web');
            if (href && !isEditorEnabled && !isNewWindow && !isInIframe) {
                window.top.location.replace(href);
            }
        });

    }
});
