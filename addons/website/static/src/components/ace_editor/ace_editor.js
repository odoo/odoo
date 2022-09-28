/** @odoo-module */

import {ComponentAdapter} from 'web.OwlCompatibility';
import {useService} from '@web/core/utils/hooks';
import AceEditor from 'web_editor.ace';

const {Component} = owl;

export const WebsiteAceEditor = AceEditor.extend({
    mainParam: 'advanced-view-editor',
    resParam: 'res',

    start() {
        const resId = new URL(window.location).searchParams.get(this.resParam);
        if (resId) {
            this.options.initialResID = resId;
        }
        this._super(...arguments);
        this._updateURL();
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    do_hide() {
        const url = new URL(window.location);
        url.searchParams.delete(this.mainParam);
        url.searchParams.delete(this.resParam);
        window.history.replaceState({}, '', url);
        this.cleanIframeUrl();
        this.options.toggleAceEditor(false);
    },
    cleanIframeUrl() {
        const iframeEl = document.querySelector('iframe.o_iframe');
        const src = decodeURIComponent(iframeEl.getAttribute('src'));
        const paramsString = src.slice(src.lastIndexOf('?') + 1);
        const searchParams = new URLSearchParams(paramsString);
        if (searchParams.has(this.mainParam)) {
            // If the user reloaded the page while the ACE editor was open,
            // the iframe has unwanted parameters in its src.
            searchParams.delete(this.mainParam);
            searchParams.delete(this.resParam);
            iframeEl.setAttribute('src', `${src.slice(0, src.lastIndexOf('?'))}?${searchParams.toString()}`);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _saveResources() {
        return this._super.apply(this, arguments).then(() => {
            const defs = [];
            if (this.currentType === 'xml') {
                // When saving a view, the view ID might change. Thus, the
                // active ID in the URL will be incorrect. After the save
                // reload, that URL ID won't be found and JS will crash.
                // We need to find the new ID (either because the view became
                // specific or because its parent was edited too and the view
                // got copy/unlink).
                const selectedView = _.findWhere(this.views, {id: this._getSelectedResource()});
                let context;
                this.trigger_up('context_get', {
                    callback: (ctx) => {
                        context = ctx;
                    },
                });
                defs.push(this._rpc({
                    model: 'ir.ui.view',
                    method: 'search_read',
                    fields: ['id'],
                    domain: [['key', '=', selectedView.key], ['website_id', '=', context.website_id]],
                }));
            }
            return Promise.all(defs).then((async () => {
                await this._updateEditor();
                this.options.reload();
            }));
        });
    },
    _displayResource: function () {
        this._super.apply(this, arguments);
        this._updateURL();
    },
    /**
     * @override
     */
    _switchType(type) {
        const ret = this._super(...arguments);

        if (type === 'scss') {
            // By default show the user_custom_rules.scss one as some people
            // would write rules in user_custom_bootstrap_overridden.scss
            // otherwise, not reading the comment inside explaining how that
            // file should be used.
            this._displayResource('/website/static/src/scss/user_custom_rules.scss');
        }

        return ret;
    },
    /**
     * @override
     */
    _resetResource() {
        return this._super.apply(this, arguments).then((() => {
            this._updateEditor();
            this.options.reload();
        }).bind(this));
    },
    /**
     * Used to update UI (resource display, toggle resetButton visibility,...)
     * on save/reset since we reload the iframe only after an update.
     *
     * @private
     */
    async _updateEditor() {
        if (['js', 'scss'].includes(this.currentType)) {
            await this._loadResources();
            return this._displayResource(this._getSelectedResource());
        }
    },
    /**
     * @override
     */
    _rpc(options) {
        let context;
        this.trigger_up('context_get', {
            callback: (ctx) => {
                context = ctx;
            },
        });
        return this._super({...options, context: context});
    },
    _updateURL: function (resID) {
        resID = resID || this._getSelectedResource();
        window.history.replaceState({}, '', `?${this.mainParam}=true&${this.resParam}=${resID}`);
    },
});

export class AceEditorAdapterComponent extends ComponentAdapter {
    setup() {
        super.setup();

        this.website = useService("website");
        this.user = useService("user");
        this.env = Component.env;
    }

    _trigger_up(event) {
        if (event.name === 'context_get') {
            return event.data.callback({...this.user.context, website_id: this.website.currentWebsite.id});
        }
        super._trigger_up(event);
    }

    /**
     * @override
     */
    get widgetArgs() {
        return [
            this.website.pageDocument && this.website.pageDocument.documentElement.dataset.viewXmlid,
            {
                toggleAceEditor: () => this.website.context.showAceEditor = false,
                defaultBundlesRestriction: [
                    'web.assets_frontend',
                    'web.assets_frontend_minimal',
                    'web.assets_frontend_lazy',
                ],
                reload: () => {
                    this.website.keepAceOpen = true;
                    this.website.contentWindow.location.reload();
                    delete this.website.keepAceOpen;
                },
            }
        ];
    }
}
AceEditorAdapterComponent.defaultProps = {
    Component: WebsiteAceEditor,
};
