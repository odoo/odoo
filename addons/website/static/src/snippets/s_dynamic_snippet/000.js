odoo.define('website.s_dynamic_snippet', function (require) {
'use strict';

const core = require('web.core');
const config = require('web.config');
const publicWidget = require('web.public.widget');

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
                this._manageWarningMessageVisibility()
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
                this._render();
                this._toggleVisibility(true);
            });
    },
    /**
     *
     * @override
     */
    destroy: function () {
        this._toggleVisibility(false);
        this._setupSizeChangedManagement(false);
        this._clearContent();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     */
    _clearContent: function () {
        const $dynamicSnippetTemplate = this.$el.find('.dynamic_snippet_template');
        if ($dynamicSnippetTemplate) {
            $dynamicSnippetTemplate.html('');
        }
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
     * Fetches the data.
     * @private
     */
    _fetchData: function () {
        if (this._isConfigComplete()) {
            return this._rpc(
                {
                    'route': '/website/snippet/filters',
                    'params': {
                        'filter_id': parseInt(this.$el.get(0).dataset.filterId),
                        'template_key': this.$el.get(0).dataset.templateKey,
                        'limit': parseInt(this.$el.get(0).dataset.numberOfRecords),
                        'search_domain': this._getSearchDomain()
                    },
                })
                .then(
                    (data) => {
                        this.data = data;
                    }
                );
        } else {
            return new Promise((resolve) => {
                this.data = [];
                resolve();
            });
        }
    },
    /**
     *
     * @private
     */
    _mustMessageWarningBeHidden: function() {
        return this._isConfigComplete() || !this.editableMode;
    },
    /**
     *
     * @private
     */
    _manageWarningMessageVisibility: async function () {
        this.$el.find('.missing_option_warning').toggleClass(
            'd-none',
            this._mustMessageWarningBeHidden()
        );
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
        if (this.data.length) {
            this._prepareContent();
        } else {
            this.renderedContent = '';
        }
        this._renderContent();
    },
    /**
     *
     * @private
     */
    _renderContent: function () {
        this.$el.find('.dynamic_snippet_template').html(this.renderedContent);
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
        this.$el.toggleClass('d-none', !visible);
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
