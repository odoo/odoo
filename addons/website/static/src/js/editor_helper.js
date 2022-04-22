/** @odoo-module */

import createPublicRoot from '../js/content/website_root_instance';

// FIXME: Should be made more robust to ensure we're in edit mode.
if (window.parent !== window) {
    createPublicRoot.then(rootInstance => window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}})));
}
