odoo.define('website.s_dynamic_snippet', function (require) {
'use strict';

const core = require('web.core');
const config = require('web.config');
const publicWidget = require('web.public.widget');
const {Markup} = require('web.utils');

const DynamicSnippet = publicWidget.Widget.extend({
    selector: '.s_dynamic_snippet',
    xmlDependencies: ['/website/static/src/snippets/s_dynamic_snippet/000.xml'],
    read_events: {
        'click [data-url]': '_onCallToAction',
    },
    disabledInEditableMode: false,

    /**
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        /**
         * The dynamic filter data source data formatted with the chosen template.
         * Can be accessed when overriding the _render_content() function in order to generate
         * a new renderedContent from the original data.
         *
         * @type {*|jQuery.fn.init|jQuery|HTMLElement}
         */
        this.data = [];
        this.renderedContent = '';
        this.isDesplayedAsMobile = config.device.isMobile;
        this.uniqueId = _.uniqueId('s_dynamic_snippet_');
        this.template_key = 'website.s_dynamic_snippet.grid';
    },
    /**
     *
     * @override
     */
    willStart: function () {
        return this._super.apply(this, arguments).then(
            () => Promise.all([
                this._fetchData(),
            ])
        );
    },
    /**
     *
     * @override
     */
    start: function () {
        return this._super.apply(this, arguments)
            .then(() => {
                this._setupSizeChangedManagement(true);
                this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
                this._render();
                this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
            });
    },
    /**
     *
     * @override
     */
    destroy: function () {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        this._toggleVisibility(false);
        this._setupSizeChangedManagement(false);
        this._clearContent();
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _clearContent: function () {
        const $templateArea = this.$el.find('.dynamic_snippet_template');
        this.trigger_up('widgets_stop_request', {
            $target: $templateArea,
        });
        $templateArea.html('');
    },
    /**
     * Method to be overridden in child components if additional configuration elements
     * are required in order to fetch data.
     * @private
     */
    _isConfigComplete: function () {
        return this.$el.get(0).dataset.filterId !== undefined && this.$el.get(0).dataset.templateKey !== undefined;
    },
    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @private
     */
    _getSearchDomain: function () {
        return [];
    },
    /**
     * Method to be overridden in child components in order to add custom parameters if needed.
     * @private
     */
    _getRpcParameters: function () {
        return {};
    },
    /**
     * Fetches the data.
     * @private
     */
    async _fetchData() {
        if (this._isConfigComplete()) {
            const nodeData = this.el.dataset;
            const filterFragments = await this._rpc({
                'route': '/website/snippet/filters',
                'params': Object.assign({
                    'filter_id': parseInt(nodeData.filterId),
                    'template_key': nodeData.templateKey,
                    'limit': parseInt(nodeData.numberOfRecords),
                    'search_domain': this._getSearchDomain(),
                    'with_sample': this.editableMode,
                }, this._getRpcParameters()),
            });
            this.data = filterFragments.map(Markup);
        } else {
            this.data = [];
        }
    },
    /**
     * Method to be overridden in child components in order to prepare content
     * before rendering.
     * @private
     */
    _prepareContent: function () {
        if (this.$target[0].dataset.numberOfElements && this.$target[0].dataset.numberOfElementsSmallDevices) {
            this.renderedContent = core.qweb.render(
                this.template_key,
                this._getQWebRenderOptions());
        } else {
            this.renderedContent = '';
        }
    },
    /**
     * Method to be overridden in child components in order to prepare QWeb
     * options.
     * @private
     */
    _getQWebRenderOptions: function () {
        return {
            chunkSize: parseInt(
                config.device.isMobile
                    ? this.$target[0].dataset.numberOfElementsSmallDevices
                    : this.$target[0].dataset.numberOfElements
            ),
            data: this.data,
            uniqueId: this.uniqueId
        };
    },
    /**
     *
     * @private
     */
    _render: function () {
        if (this.data.length > 0 || this.editableMode) {
            this.$el.removeClass('o_dynamic_empty');
            this._prepareContent();
        } else {
            this.$el.addClass('o_dynamic_empty');
            this.renderedContent = '';
        }
        // TODO Remove in master: adapt already existing snippet from former version.
        if (this.$el[0].classList.contains('d-none') && !this.$el[0].classList.contains('d-md-block')) {
            // Remove the 'd-none' of the old template if it is not related to
            // the visible on mobile option.
            this.$el[0].classList.remove('d-none');
        }
        this._renderContent();
    },
    /**
     * @private
     */
    _renderContent: function () {
        const $templateArea = this.$el.find('.dynamic_snippet_template');
        this.trigger_up('widgets_stop_request', {
            $target: $templateArea,
        });
        $templateArea.html(this.renderedContent);
        // TODO this is probably not the only public widget which creates DOM
        // which should be attached to another public widget. Maybe a generic
        // method could be added to properly do this operation of DOM addition.
        this.trigger_up('widgets_start_request', {
            $target: $templateArea,
            editableMode: this.editableMode,
        });
    },
    /**
     *
     * @param {Boolean} enable
     * @private
     */
    _setupSizeChangedManagement: function (enable) {
        if (enable === true) {
            config.device.bus.on('size_changed', this, this._onSizeChanged);
        } else {
            config.device.bus.off('size_changed', this, this._onSizeChanged);
        }
    },
    /**
     *
     * @param visible
     * @private
     */
    _toggleVisibility: function (visible) {
        this.$el.toggleClass('o_dynamic_empty', !visible);
    },

    //------------------------------------- -------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Navigates to the call to action url.
     * @private
     */
    _onCallToAction: function (ev) {
        window.location = $(ev.currentTarget).attr('data-url');
    },
    /**
     * Called when the size has reached a new bootstrap breakpoint.
     *
     * @private
     * @param {number} size as Integer @see web.config.device.SIZES
     */
    _onSizeChanged: function (size) {
        if (this.isDesplayedAsMobile !== config.device.isMobile) {
            this.isDesplayedAsMobile = config.device.isMobile;
            this._render();
        }
    },
});

publicWidget.registry.dynamic_snippet = DynamicSnippet;

return DynamicSnippet;

});
