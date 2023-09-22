/** @odoo-module */

import { useWidget } from "@web/legacy/utils";
import {useService} from '@web/core/utils/hooks';
import AceEditor from '@web_editor/js/common/ace';

import { Component, xml } from "@odoo/owl";

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
    _getContext() {
        return this.options.getContext();
    },
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
                const selectedView = Object.values(this.views).find(view => view.id === this._getSelectedResource());
                const context = this.options.getContext();
                defs.push(
                    this.orm.searchRead(
                        "ir.ui.view",
                        [
                            ["key", "=", selectedView.key],
                            ["website_id", "=", context.website_id],
                        ],
                        ["id"],
                        { context: this.options.getContext() }
                    )
                );
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
});

export class AceEditorAdapterComponent extends Component {
    static template = xml`<div style="display: contents;" t-ref="wrapper"/>`;

    setup() {
        this.website = useService("website");
        this.user = useService("user");
        this.env = Component.env;

        useWidget("wrapper", WebsiteAceEditor, [
            this.website.pageDocument && this.website.pageDocument.documentElement.dataset.viewXmlid,
            {
                toggleAceEditor: () => this.website.context.showAceEditor = false,
                defaultBundlesRestriction: [
                    'web.assets_frontend',
                    'web.assets_frontend_minimal',
                    'web.assets_frontend_lazy',
                ],
                reload: () => {
                    this.website.contentWindow.location.reload();
                },
                getContext: () => ({
                    ...this.user.context,
                    website_id: this.website.currentWebsite.id,
                }),
            },
        ]);
    }
}
