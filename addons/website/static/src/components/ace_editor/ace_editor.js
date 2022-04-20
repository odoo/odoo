/** @odoo-module */

import {ComponentAdapter} from 'web.OwlCompatibility';
import {useService} from '@web/core/utils/hooks';
import AceEditor from 'web_editor.ace';

const {Component} = owl;

export const WebsiteAceEditor = AceEditor.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    do_hide() {
        this.options.toggleAceEditor(false);
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
                toggleAceEditor: this.props.toggleAceEditor,
                defaultBundlesRestriction: [
                    'web.assets_frontend',
                    'web.assets_frontend_minimal',
                    'web.assets_frontend_lazy',
                ],
                reload: () => {
                    this.website.contentWindow.location.reload();
                },
            }
        ];
    }

}
