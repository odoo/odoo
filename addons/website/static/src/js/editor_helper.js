/** @odoo-module */

import createPublicRoot from '../js/content/website_root_instance';

if (window.parent !== window) {
    createPublicRoot.then(rootInstance => window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}})));
}
