/** @odoo-module */

import options from 'web_editor.snippets.options';

options.registry.MasonryLayout = options.Class.extend({
    custom_events: Object.assign({}, options.Class.prototype.custom_events, {
        'user_value_widget_opening': '_onWidgetOpening',
    }),

    /**
     * @constructor
     */
    async start() {
        this.containerEl = this.$target.find('> .container, > .container-fluid, > .o_container_small')[0];
        this._templates = {};
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the masonry snippet layout.
     *
     * @see this.selectClass for parameters
     */
    async selectMasonryTemplate(previewMode, widgetValue, params) {
        await this._templatesLoading;

        if (previewMode === 'reset') {
            if (!this.beforePreviewNodes) {
                // FIXME should not be necessary: only needed because we have a
                // strange 'reset' sent after a non-preview
                return;
            }

            // Empty the container and restore the original content
            while (this.containerEl.lastChild) {
                this.containerEl.removeChild(this.containerEl.lastChild);
            }
            for (const node of this.beforePreviewNodes) {
                this.containerEl.appendChild(node);
            }
            this.beforePreviewNodes = null;
            return;
        }

        if (!this.beforePreviewNodes) {
            // We are about the apply a template on non-previewed content,
            // save that content's nodes.
            this.beforePreviewNodes = [...this.containerEl.childNodes];
        }
        // Empty the container and add the template content
        while (this.containerEl.lastChild) {
            this.containerEl.removeChild(this.containerEl.lastChild);
        }
        this.containerEl.insertAdjacentHTML('beforeend', this._templates[widgetValue]);

        if (!previewMode) {
            // The original content to keep saved has to be retrieved just
            // before the preview (if we save it now, we might miss other items
            // added by other options or custo).
            this.beforePreviewNodes = null;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onWidgetOpening(ev) {
        if (this._templatesLoading || ev.target.getName() !== 'masonry_template_opt') {
            return;
        }
        const templateParams = ev.target.getMethodsParams('selectMasonryTemplate');
        const proms = templateParams.possibleValues.map(async xmlid => {
            if (!xmlid) {
                return;
            }
            // TODO should be better and retrieve all rendering in one RPC (but
            // those ~10 RPC are only done once per edit mode if masonry snippet
            // option is opened, so I guess this is acceptable).
            this._templates[xmlid] = await this._rpc({
                model: 'ir.ui.view',
                method: 'render_public_asset',
                args: [`${xmlid}`, {}],
                kwargs: {
                    context: this.options.context,
                },
            });
        });
        this._templatesLoading = Promise.all(proms);
    },
});
