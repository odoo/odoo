/** @odoo-module */
// Legacy services
import legacyEnv from 'web.commonEnv';
import { useService } from '@web/core/utils/hooks';
import { WysiwygAdapterComponent } from '../wysiwyg_adapter/wysiwyg_adapter';

const { markup, Component, useState, useChildSubEnv, useEffect, onWillStart, onMounted } = owl;

export class WebsiteEditorComponent extends Component {
    /**
     * @override
     */
    setup() {
        this.websiteService = useService('website');
        this.notificationService = useService('notification');

        this.websiteContext = useState(this.websiteService.context);
        this.state = useState({
            reloading: false,
            showWysiwyg: false,
        });
        this.wysiwygOptions = {};

        useChildSubEnv(legacyEnv);

        onWillStart(async () => {
            this.websiteService.blockIframe(false);
            this.Wysiwyg = await this.websiteService.loadWysiwyg();
        });

        useEffect(isPublicRootReady => {
            if (isPublicRootReady) {
                this.publicRootReady();
            }
        }, () => [this.websiteContext.isPublicRootReady]);

        onMounted(() => {
            if (this.websiteContext.isPublicRootReady) {
                this.publicRootReady();
            }
        });
    }
    /**
     * Starts the wysiwyg or disable edition if currently
     * on a translated page.
     */
    publicRootReady() {
        if (this.websiteService.currentWebsite.metadata.translatable) {
            this.websiteContext.edition = false;
            this.websiteService.unblockIframe();
        } else {
            this.state.showWysiwyg = true;
        }
    }
    /**
     * Displays the side menu and unblock the iframe to
     * start edition.
     */
    wysiwygReady() {
        this.websiteContext.snippetsLoaded = true;
        this.state.reloading = false;
        this.wysiwygOptions.invalidateSnippetCache = false;
        this.websiteService.unblockIframe();
    }
    /**
     * Prepares the editor for reload. Copies the widget element tree
     * to display it as a skeleton so that it doesn't flash when the editor
     * is destroyed and re-started.
     *
     * @param widgetEl {HTMLElement} Widget element of the editor to copy.
     */
    willReload(widgetEl) {
        this.websiteService.blockIframe();
        if (widgetEl) {
            widgetEl.querySelectorAll('#oe_manipulators').forEach(el => el.remove());
            widgetEl.querySelectorAll('we-input input').forEach(input => {
                input.setAttribute('value', input.closest('we-input').dataset.selectStyle || '');
            });
            this.loadingDummy = markup(widgetEl.innerHTML);
        }
        this.state.reloading = true;
    }
    /**
     * Dismount the editor and reload the iframe.
     *
     * @param snippetOptionSelector {string} Selector to refocus the editor once reloaded.
     * @param [url] {string} URL to reload the iframe tp
     * @param invalidateSnippetCache {boolean} If the SnippetMenu needs to reload the Snippets from server.
     * @returns {Promise<void>}
     */
    async reload({ snippetOptionSelector, url, invalidateSnippetCache } = {}) {
        this.notificationService.add(this.env._t("Your modifications were saved to apply this option."), {
            title: this.env._t("Content saved."),
            type: 'success'
        });
        if (invalidateSnippetCache) {
            this.wysiwygOptions.invalidateSnippetCache = true;
        }
        this.state.showWysiwyg = false;
        await this.props.reloadIframe(url);
        this.reloadSelector = snippetOptionSelector;
    }
    /**
     * Blocks the iframe and start the hiding transition.
     *
     * @returns {Promise<void>}
     */
    async quit() {
        this.websiteService.blockIframe(true, 400);
        document.body.classList.remove('editor_has_snippets');
        this.websiteContext.snippetsLoaded = false;
        setTimeout(this.destroyAfterTransition.bind(this), 400);
    }
    /**
     * Dismounts the editor.
     *
     * @returns {Promise<void>}
     */
    async destroyAfterTransition() {
        this.state.showWysiwyg = false;
        await this.props.reloadIframe();
        this.websiteContext.edition = false;
        this.websiteService.unblockIframe();
    }
}
WebsiteEditorComponent.components = { WysiwygAdapterComponent };
WebsiteEditorComponent.template = 'website.WebsiteEditorComponent';
