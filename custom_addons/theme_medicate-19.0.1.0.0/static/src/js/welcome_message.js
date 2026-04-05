/** @odoo-module **/
import { Component } from '@odoo/owl';
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';
import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";


patch(WebsitePreview.prototype, {
     addWelcomeMessage() {
         if (this.websiteService.isRestrictedEditor) {
            const wrap = this.iframe.el.contentDocument.querySelector('#wrapwrap.homepage #wrap');
            if (wrap && !wrap.innerHTML.trim()) {
                this.welcomeMessage = renderToElement('website.homepage_editor_welcome_message');
                this.welcomeMessage.classList.add('o_homepage_editor_welcome_message', 'h-100');
                while (wrap.firstChild) {
                    wrap.removeChild(wrap.lastChild);
                }
            }
        }
    }
});
