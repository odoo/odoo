/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { uniqueId } from "@web/core/utils/functions";
import { renderToString } from "@web/core/utils/render";
import { listenSizeChange, utils as uiUtils } from "@web/core/ui/ui_service";

import { markup } from "@odoo/owl";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 1;

const DynamicSnippet = publicWidget.Widget.extend({
    selector: '.s_dynamic_snippet',
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
        this.isDesplayedAsMobile = uiUtils.isSmall();
        this.unique_id = uniqueId("s_dynamic_snippet_");
        this.template_key = 'website.s_dynamic_snippet.grid';

        this.rpc = this.bindService("rpc");
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
            const filterFragments = await this.rpc(
                '/website/snippet/filters',
                Object.assign({
                    'filter_id': parseInt(nodeData.filterId),
                    'template_key': nodeData.templateKey,
                    'limit': parseInt(nodeData.numberOfRecords),
                    'search_domain': this._getSearchDomain(),
                    'with_sample': this.editableMode,
                }, this._getRpcParameters())
            );
            this.data = filterFragments.map(markup);
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
        this.renderedContent = renderToString(
            this.template_key,
            this._getQWebRenderOptions()
        );
    },
    /**
     * Method to be overridden in child components in order to prepare QWeb
     * options.
     * @private
     */
     _getQWebRenderOptions: function () {
        const dataset = this.el.dataset;
        const numberOfRecords = parseInt(dataset.numberOfRecords);
        let numberOfElements;
        if (uiUtils.isSmall()) {
            numberOfElements = parseInt(dataset.numberOfElementsSmallDevices) || DEFAULT_NUMBER_OF_ELEMENTS_SM;
        } else {
            numberOfElements = parseInt(dataset.numberOfElements) || DEFAULT_NUMBER_OF_ELEMENTS;
        }
        const chunkSize = numberOfRecords < numberOfElements ? numberOfRecords : numberOfElements;
        return {
            chunkSize: chunkSize,
            data: this.data,
            unique_id: this.unique_id,
            extraClasses: dataset.extraClasses || '',
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
        this._renderContent();
        this.trigger_up('widgets_start_request', {
            $target: this.$el.children(),
            options: {parent: this},
            editableMode: this.editableMode,
        });
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
            this.removeSizeListener = listenSizeChange(this._onSizeChanged.bind(this));
        } else {
            this.removeSizeListener();
            delete this.removeSizeListener;
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
     */
    _onSizeChanged: function () {
        if (this.isDesplayedAsMobile !== uiUtils.isSmall()) {
            this.isDesplayedAsMobile = uiUtils.isSmall();
            this._render();
        }
    },
});

publicWidget.registry.dynamic_snippet = DynamicSnippet;

export default DynamicSnippet;
