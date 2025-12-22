/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';
import {
    markup,
    Component,
    useState,
    useEffect,
    onWillStart,
    onMounted,
    onWillUnmount,
} from "@odoo/owl";

export class WebsiteEditorComponent extends Component {
    static template = "website.WebsiteEditorComponent";
    static props = ["*"];
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

        onWillStart(async () => {
            await this.websiteService.loadWysiwyg();
            const adapterModule = await odoo.loader.modules.get('@website/components/wysiwyg_adapter/wysiwyg_adapter');
            this.WysiwygAdapterComponent = adapterModule.WysiwygAdapterComponent;
        });

        useEffect(isPublicRootReady => {
            if (isPublicRootReady) {
                this.publicRootReady();
            }
        }, () => [this.websiteContext.isPublicRootReady]);

        onMounted(() => {
            this.websiteService.blockPreview(false);
            if (this.websiteContext.isPublicRootReady) {
                this.publicRootReady();
            }
        });

        onWillUnmount(() => {
            if (this.onWillUnmount) {
                this.onWillUnmount();
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
            this.websiteService.unblockPreview();
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
        if (this.state.reloading) {
            document.body.classList.remove('editor_has_dummy_snippets');
            this.state.reloading = false;
        }
        this.websiteService.unblockPreview();
        // setTimeout ensure transition on Firefox
        setTimeout(() => document.body.classList.add("o_website_navbar_transition_hide"));
        setTimeout(() => document.body.classList.add("o_website_navbar_hide"), 400);
    }
    /**
     * Prepares the editor for reload. Copies the widget element tree
     * to display it as a skeleton so that it doesn't flash when the editor
     * is destroyed and re-started.
     *
     * @param widgetEl {HTMLElement} Widget element of the editor to copy.
     */
    willReload(widgetEl) {
        this.websiteService.blockPreview();
        if (widgetEl) {
            this.loadingDummy = markup(widgetEl.innerHTML);
        }
        this.state.reloading = true;
        document.body.classList.add('editor_has_dummy_snippets');
    }
    /**
     * Dismount the editor and reload the iframe.
     *
     * @param snippetOptionSelector {string} Selector to refocus the editor once reloaded.
     * @param [url] {string} URL to reload the iframe tp
     * @returns {Promise<void>}
     */
    async reload({ snippetOptionSelector, url } = {}) {
        this.notificationService.add(_t("Your modifications were saved to apply this option."), {
            title: _t("Content saved."),
            type: 'success'
        });
        this.state.showWysiwyg = false;
        await this.props.reloadIframe(url);
        this.reloadSelector = snippetOptionSelector;
    }
    /**
     * Blocks the iframe and start the hiding transition.
     * @param {Boolean} [reloadIframe=true]
     * @param {Function} onLeave A callback that will be played after the
     * transition, when the component is unmounted.
     * @returns {Promise<void>}
     */
    async quit({ reloadIframe = true, onLeave } = {}) {
        this.onWillUnmount = onLeave;
        if (reloadIframe) {
            this.websiteService.blockPreview();
            await this.props.reloadIframe();
            this.websiteService.unblockPreview();
        }
        this.websiteContext.snippetsLoaded = false;
        document.body.classList.remove("o_website_navbar_hide");
        setTimeout(() => document.body.classList.remove("o_website_navbar_transition_hide"));
        setTimeout(this.destroyAfterTransition.bind(this), 400);
    }
    /**
     * Dismounts the editor.
     *
     * @returns {Promise<void>}
     */
    destroyAfterTransition() {
        this.state.showWysiwyg = false;
        this.websiteContext.edition = false;
    }
}
