odoo.define('website_sale.editor', function (require) {
'use strict';

var options = require('web_editor.snippets.options');
const Wysiwyg = require('website.wysiwyg');
const { ComponentWrapper } = require('web.OwlCompatibility');
const { MediaDialog, MediaDialogWrapper } = require('@web_editor/components/media_dialog/media_dialog');
const { useWowlService } = require('@web/legacy/utils');
const {qweb, _t} = require('web.core');
const {Markup} = require('web.utils');
const Dialog = require('web.Dialog');

const { onRendered } = owl;

Wysiwyg.include({
    custom_events: Object.assign(Wysiwyg.prototype.custom_events, {
        get_ribbons: '_onGetRibbons',
        get_ribbon_classes: '_onGetRibbonClasses',
        delete_ribbon: '_onDeleteRibbon',
        set_ribbon: '_onSetRibbon',
        set_product_ribbon: '_onSetProductRibbon',
    }),

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        let ribbons = [];
        if (this._isProductListPage()) {
            ribbons = await this._rpc({
                model: 'product.ribbon',
                method: 'search_read',
                fields: ['id', 'html', 'bg_color', 'text_color', 'html_class'],
            });
        }
        this.ribbons = Object.fromEntries(ribbons.map(ribbon => {
            ribbon.html = Markup(ribbon.html);
            return [ribbon.id, ribbon];
        }));
        this.originalRibbons = Object.assign({}, this.ribbons);
        this.productTemplatesRibbons = [];
        this.deletedRibbonClasses = '';
        return _super(...arguments);
    },
    /**
     * @override
     */
    async _saveViewBlocks() {
        const _super = this._super.bind(this);
        await this._saveRibbons();
        return _super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Saves the ribbons in the database.
     *
     * @private
     */
    async _saveRibbons() {
        if (!this._isProductListPage()) {
            return;
        }
        const originalIds = Object.keys(this.originalRibbons).map(id => parseInt(id));
        const currentIds = Object.keys(this.ribbons).map(id => parseInt(id));

        const ribbons = Object.values(this.ribbons);
        const created = ribbons.filter(ribbon => !originalIds.includes(ribbon.id));
        const deletedIds = originalIds.filter(id => !currentIds.includes(id));
        const modified = ribbons.filter(ribbon => {
            if (created.includes(ribbon)) {
                return false;
            }
            const original = this.originalRibbons[ribbon.id];
            return Object.entries(ribbon).some(([key, value]) => value !== original[key]);
        });

        const proms = [];
        let createdRibbonIds;
        if (created.length > 0) {
            proms.push(this._rpc({
                method: 'create',
                model: 'product.ribbon',
                args: [created.map(ribbon => {
                    ribbon = Object.assign({}, ribbon);
                    delete ribbon.id;
                    return ribbon;
                })],
            }).then(ids => createdRibbonIds = ids));
        }

        modified.forEach(ribbon => proms.push(this._rpc({
            method: 'write',
            model: 'product.ribbon',
            args: [[ribbon.id], ribbon],
        })));

        if (deletedIds.length > 0) {
            proms.push(this._rpc({
                method: 'unlink',
                model: 'product.ribbon',
                args: [deletedIds],
            }));
        }

        await Promise.all(proms);
        const localToServer = Object.assign(
            this.ribbons,
            Object.fromEntries(created.map((ribbon, index) => [ribbon.id, {id: createdRibbonIds[index]}])),
            {'false': {id: false}},
        );

        // Building the final template to ribbon-id map
        const finalTemplateRibbons = this.productTemplatesRibbons.reduce((acc, {templateId, ribbonId}) => {
            acc[templateId] = ribbonId;
            return acc;
        }, {});
        // Inverting the relationship so that we have all templates that have the same ribbon to reduce RPCs
        const ribbonTemplates = Object.entries(finalTemplateRibbons).reduce((acc, [templateId, ribbonId]) => {
            if (!acc[ribbonId]) {
                acc[ribbonId] = [];
            }
            acc[ribbonId].push(parseInt(templateId));
            return acc;
        }, {});
        const setProductTemplateRibbons = Object.entries(ribbonTemplates)
            // If the ribbonId that the template had no longer exists, remove the ribbon (id = false)
            .map(([ribbonId, templateIds]) => {
                const id = currentIds.includes(parseInt(ribbonId)) ? ribbonId : false;
                return [id, templateIds];
            }).map(([ribbonId, templateIds]) => this._rpc({
                method: 'write',
                model: 'product.template',
                args: [templateIds, {'website_ribbon_id': localToServer[ribbonId].id}],
            }));
        return Promise.all(setProductTemplateRibbons);
    },
    /**
     * Checks whether the current page is the product list.
     *
     * @private
     */
    _isProductListPage() {
        return this.options.editable && this.options.editable.find('#products_grid').length !== 0;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Returns a copy of this.ribbons through a callback.
     *
     * @private
     */
    _onGetRibbons(ev) {
        ev.data.callback(Object.assign({}, this.ribbons));
    },
    /**
     * Returns all ribbon classes, current and deleted, so they can be removed.
     *
     * @private
     */
    _onGetRibbonClasses(ev) {
        const classes = Object.values(this.ribbons).reduce((classes, ribbon) => {
            return classes + ` ${ribbon.html_class}`;
        }, '') + this.deletedRibbonClasses;
        ev.data.callback(classes);
    },
    /**
     * Deletes a ribbon.
     *
     * @private
     */
    _onDeleteRibbon(ev) {
        this.deletedRibbonClasses += ` ${this.ribbons[ev.data.id].html_class}`;
        delete this.ribbons[ev.data.id];
    },
    /**
     * Sets a ribbon;
     *
     * @private
     */
    _onSetRibbon(ev) {
        const {ribbon} = ev.data;
        const previousRibbon = this.ribbons[ribbon.id];
        if (previousRibbon) {
            this.deletedRibbonClasses += ` ${previousRibbon.html_class}`;
        }
        this.ribbons[ribbon.id] = ribbon;
    },
    /**
     * Sets which ribbon is used by a product template.
     *
     * @private
     */
    _onSetProductRibbon(ev) {
        const {templateId, ribbonId} = ev.data;
        this.productTemplatesRibbons.push({templateId, ribbonId});
    },
});

options.registry.WebsiteSaleGridLayout = options.Class.extend({

    /**
     * @override
     */
    start: function () {
        this.ppg = parseInt(this.$target.closest('[data-ppg]').data('ppg'));
        this.ppr = parseInt(this.$target.closest('[data-ppr]').data('ppr'));
        this.default_sort = this.$target.closest('[data-default-sort]').data('default-sort');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        var listLayoutEnabled = this.$target.closest('#products_grid').hasClass('o_wsale_layout_list');
        this.$el.filter('.o_wsale_ppr_submenu').toggleClass('d-none', listLayoutEnabled);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    setPpg: function (previewMode, widgetValue, params) {
        const ppg = parseInt(widgetValue);
        if (!ppg || ppg < 1) {
            return false;
        }
        this.ppg = ppg;
        return this._rpc({
            route: '/shop/config/website',
            params: {
                'shop_ppg': ppg,
            },
        });
    },
    /**
     * @see this.selectClass for params
     */
    setPpr: function (previewMode, widgetValue, params) {
        this.ppr = parseInt(widgetValue);
        this._rpc({
            route: '/shop/config/website',
            params: {
                'shop_ppr': this.ppr,
            },
        });
    },
    /**
     * @see this.selectClass for params
     */
    setDefaultSort: function (previewMode, widgetValue, params) {
        this.default_sort = widgetValue;
        this._rpc({
            route: '/shop/config/website',
            params: {
                'shop_default_sort': this.default_sort,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);
        const pprSelector = this.el.querySelector('.o_wsale_ppr_submenu.d-none');
        this.el.querySelector('.o_wsale_ppr_by').classList.toggle('d-none', pprSelector);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'setPpg': {
                return this.ppg;
            }
            case 'setPpr': {
                return this.ppr;
            }
            case 'setDefaultSort': {
                return this.default_sort;
            }
        }
        return this._super(...arguments);
    },
});

options.registry.WebsiteSaleProductsItem = options.Class.extend({
    events: _.extend({}, options.Class.prototype.events || {}, {
        'mouseenter .o_wsale_soptions_menu_sizes table': '_onTableMouseEnter',
        'mouseleave .o_wsale_soptions_menu_sizes table': '_onTableMouseLeave',
        'mouseover .o_wsale_soptions_menu_sizes td': '_onTableItemMouseEnter',
        'click .o_wsale_soptions_menu_sizes td': '_onTableItemClick',
    }),

    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);
        this.ppr = this.$target.closest('[data-ppr]').data('ppr');
        this.productTemplateID = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));
        this.ribbons = await new Promise(resolve => this.trigger_up('get_ribbons', {callback: resolve}));
        this.$ribbon = this.$target.find('.o_ribbon');
        return _super(...arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        var listLayoutEnabled = this.$target.closest('#products_grid').hasClass('o_wsale_layout_list');
        this.$el.find('.o_wsale_soptions_menu_sizes')
            .toggleClass('d-none', listLayoutEnabled);
        // Ribbons may have been edited or deleted in another products' option, need to make sure they're up to date
        this.rerender = true;
        this.ribbonEditMode = false;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        const proms = [this._super(...arguments)];
        if (params.cssProperty === 'background-color' && params.colorNames.includes(widgetValue)) {
            // Reset text-color when choosing a background-color class, so it uses the automatic text-color of the class.
            proms.push(this.selectStyle(previewMode, '', {cssProperty: 'color'}));
        }
        await Promise.all(proms);
        if (!previewMode) {
            await this._saveRibbon();
        }
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbon(previewMode, widgetValue, params) {
        if (previewMode === 'reset') {
            widgetValue = this.prevRibbonId;
        } else {
            this.prevRibbonId = this.$target[0].dataset.ribbonId;
        }
        if (!previewMode) {
            this.ribbonEditMode = false;
        }
        await this._setRibbon(widgetValue);
    },
    /**
     * @see this.selectClass for params
     */
    editRibbon(previewMode, widgetValue, params) {
        this.ribbonEditMode = !this.ribbonEditMode;
    },
    /**
     * @see this.selectClass for params
     */
    async createRibbon(previewMode, widgetValue, params) {
        await this._setRibbon(false);
        this.$ribbon.text(_t('Badge Text'));
        this.$ribbon.addClass('bg-primary o_ribbon_left');
        this.ribbonEditMode = true;
        await this._saveRibbon(true);
    },
    /**
     * @see this.selectClass for params
     */
    async deleteRibbon(previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            Dialog.confirm(this, _t('Are you sure you want to delete this badge ?'), {
                confirm_callback: () => resolve(true),
                cancel_callback: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        const {ribbonId} = this.$target[0].dataset;
        this.trigger_up('delete_ribbon', {id: ribbonId});
        this.ribbons = await new Promise(resolve => this.trigger_up('get_ribbons', {callback: resolve}));
        this.rerender = true;
        await this._setRibbon(ribbonId);
        this.ribbonEditMode = false;
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbonHtml(previewMode, widgetValue, params) {
        this.$ribbon.html(widgetValue);
        if (!previewMode) {
            await this._saveRibbon();
        }
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbonMode(previewMode, widgetValue, params) {
        this.$ribbon[0].className = this.$ribbon[0].className.replace(/o_(ribbon|tag)_(left|right)/, `o_${widgetValue}_$2`);
        await this._saveRibbon();
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbonPosition(previewMode, widgetValue, params) {
        this.$ribbon[0].className = this.$ribbon[0].className.replace(/o_(ribbon|tag)_(left|right)/, `o_$1_${widgetValue}`);
        await this._saveRibbon();
    },
    /**
     * @see this.selectClass for params
     */
    changeSequence: function (previewMode, widgetValue, params) {
        this._rpc({
            route: '/shop/config/product',
            params: {
                product_id: this.productTemplateID,
                sequence: widgetValue,
            },
        }).then(() => this._reloadEditable());
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    updateUI: async function () {
        await this._super.apply(this, arguments);

        var sizeX = parseInt(this.$target.attr('colspan') || 1);
        var sizeY = parseInt(this.$target.attr('rowspan') || 1);

        var $size = this.$el.find('.o_wsale_soptions_menu_sizes');
        $size.find('tr:nth-child(-n + ' + sizeY + ') td:nth-child(-n + ' + sizeX + ')')
             .addClass('selected');

        // Adapt size array preview to fit ppr
        $size.find('tr td:nth-child(n + ' + parseInt(this.ppr + 1) + ')').hide();
        if (this.rerender) {
            this.rerender = false;
            return this._rerenderXML();
        }
    },
    /**
     * @override
     */
    updateUIVisibility: async function () {
        // TODO: update this once updateUIVisibility can be used to compute visibility
        // of arbitrary DOM elements and not just widgets.
        await this._super(...arguments);
        this.$el.find('[data-name="ribbon_customize_opt"]').toggleClass('d-none', !this.ribbonEditMode);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const $select = $(uiFragment.querySelector('.o_wsale_ribbon_select'));
        this.ribbons = await new Promise(resolve => this.trigger_up('get_ribbons', {callback: resolve}));
        const classes = this.$ribbon[0].className;
        this.$ribbon[0].className = '';
        const defaultTextColor = window.getComputedStyle(this.$ribbon[0]).color;
        this.$ribbon[0].className = classes;
        Object.values(this.ribbons).forEach(ribbon => {
            const colorClasses = ribbon.html_class
                .split(' ')
                .filter(className => !/^o_(ribbon|tag)_(left|right)$/.test(className))
                .join(' ');
            $select.append(qweb.render('website_sale.ribbonSelectItem', {
                ribbon,
                colorClasses,
                isTag: /o_tag_(left|right)/.test(ribbon.html_class),
                isLeft: /o_(tag|ribbon)_left/.test(ribbon.html_class),
                textColor: ribbon.text_color || (colorClasses ? 'currentColor' : defaultTextColor),
            }));
        });
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const classList = this.$ribbon[0].classList;
        switch (methodName) {
            case 'setRibbon':
                return this.$target.attr('data-ribbon-id') || '';
            case 'setRibbonHtml':
                return this.$ribbon.html();
            case 'setRibbonMode': {
                if (classList.contains('o_ribbon_left') || classList.contains('o_ribbon_right')) {
                    return 'ribbon';
                }
                return 'tag';
            }
            case 'setRibbonPosition': {
                if (classList.contains('o_tag_left') || classList.contains('o_ribbon_left')) {
                    return 'left';
                }
                return 'right';
            }
        }
        return this._super(methodName, params);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'create_ribbon_opt') {
            return !this.ribbonEditMode;
        }
        return this._super(...arguments);
    },
    /**
     * Saves the ribbons.
     *
     * @private
     * @param {Boolean} [isNewRibbon=false]
     */
    async _saveRibbon(isNewRibbon = false) {
        const text = this.$ribbon.html().trim();
        const ribbon = {
            'html': text,
            'bg_color': this.$ribbon[0].style.backgroundColor,
            'text_color': this.$ribbon[0].style.color,
            'html_class': this.$ribbon.attr('class').split(' ').filter(c => !['o_ribbon'].includes(c)).join(' '),
        };
        ribbon.id = isNewRibbon ? Date.now() : parseInt(this.$target.closest('.oe_product')[0].dataset.ribbonId);
        this.trigger_up('set_ribbon', {ribbon: ribbon});
        this.ribbons = await new Promise(resolve => this.trigger_up('get_ribbons', {callback: resolve}));
        this.rerender = true;
        await this._setRibbon(ribbon.id);
    },
    /**
     * Sets the ribbon.
     *
     * @private
     * @param {integer|false} ribbonId
     */
    async _setRibbon(ribbonId) {
        this.$target[0].dataset.ribbonId = ribbonId;
        this.trigger_up('set_product_ribbon', {
            templateId: this.productTemplateID,
            ribbonId: ribbonId || false,
        });
        const ribbon = this.ribbons[ribbonId] || {html: '', bg_color: '', text_color: '', html_class: ''};
        // This option also manages other products' ribbon, therefore we need a
        // way to access all of them at once. With the content being in an iframe,
        // this is the simplest way.
        const $editableDocument = $(this.$target[0].ownerDocument.body);
        const $ribbons = $editableDocument.find(`[data-ribbon-id="${ribbonId}"] .o_ribbon`);
        $ribbons.empty().append(ribbon.html);
        let htmlClasses;
        this.trigger_up('get_ribbon_classes', {callback: classes => htmlClasses = classes});
        $ribbons.removeClass(htmlClasses);

        $ribbons.addClass(ribbon.html_class || '');
        $ribbons.css('color', ribbon.text_color || '');
        $ribbons.css('background-color', ribbon.bg_color || '');

        if (!this.ribbons[ribbonId]) {
            $editableDocument.find(`[data-ribbon-id="${ribbonId}"]`).each((index, product) => delete product.dataset.ribbonId);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onTableMouseEnter: function (ev) {
        $(ev.currentTarget).addClass('oe_hover');
    },
    /**
     * @private
     */
    _onTableMouseLeave: function (ev) {
        $(ev.currentTarget).removeClass('oe_hover');
    },
    /**
     * @private
     */
    _onTableItemMouseEnter: function (ev) {
        var $td = $(ev.currentTarget);
        var $table = $td.closest("table");
        var x = $td.index() + 1;
        var y = $td.parent().index() + 1;

        var tr = [];
        for (var yi = 0; yi < y; yi++) {
            tr.push("tr:eq(" + yi + ")");
        }
        var $selectTr = $table.find(tr.join(","));
        var td = [];
        for (var xi = 0; xi < x; xi++) {
            td.push("td:eq(" + xi + ")");
        }
        var $selectTd = $selectTr.find(td.join(","));

        $table.find("td").removeClass("select");
        $selectTd.addClass("select");
    },
    /**
     * @private
     */
    _onTableItemClick: function (ev) {
        var $td = $(ev.currentTarget);
        var x = $td.index() + 1;
        var y = $td.parent().index() + 1
        this._rpc({
            route: '/shop/config/product',
            params: {
                product_id: this.productTemplateID,
                x: x,
                y: y,
            },
        }).then(() => this._reloadEditable());
    },
    _reloadEditable() {
        return this.trigger_up('request_save', {reload: true, optionSelector: `.oe_product:has(span[data-oe-id=${this.productTemplateID}])`});
    }
});

// Small override of the MediaDialogWrapper to retrieve the attachment ids instead of img elements
class AttachmentMediaDialog extends MediaDialog {
    /**
     * @override
     */
    async save() {
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        if (selectedMedia.length) {
            this.props.save(selectedMedia);
        }
        this.props.close();
    }
}

class AttachmentMediaDialogWrapper extends MediaDialogWrapper {
    setup() {
        this.dialogs = useWowlService('dialog');

        onRendered(() => {
            this.dialogs.add(AttachmentMediaDialog, this.props);
        });
    }
}

options.registry.WebsiteSaleProductPage = options.Class.extend({

    /**
     * @override
     */
    async willStart() {
        let productProduct = this.$target[0].querySelector('[data-oe-model="product.product"]');
        let productTemplate = this.$target[0].querySelector('[data-oe-model="product.template"]');
        this.productProductID = productProduct ? productProduct.dataset.oeId : null;
        this.productTemplateID = productTemplate ? productTemplate.dataset.oeId : null;
        this.mode = "product.template";
        if (this.productProductID) {
            this.mode = "product.product"
        }

        // Different targets
        this.productDetailMain = this.$target[0].querySelector('#product_detail_main');
        this.productPageCarousel = this.$target[0].querySelector("#o-carousel-product");
        this.productPageGrid = this.$target[0].querySelector("#o-grid-product");
        return this._super(...arguments);
    },

    _updateWebsiteConfig(params) {
        this._rpc({
            route: '/shop/config/website',
            params,
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector}));
    },

    _getZoomOptionData() {
        return this._userValueWidgets.find(widget => {
            return widget.options && widget.options.dataAttributes && widget.options.dataAttributes.name === "o_wsale_zoom_mode";
        });
    },

    /**
     * @override
     */
    async setImageWidth(previewMode, widgetValue, params) {
        const zoomOption = this._getZoomOptionData();
        const updateWidth = this._updateWebsiteConfig.bind(this, { product_page_image_width: widgetValue });
        if (!zoomOption || widgetValue !== "100_pc") {
            updateWidth();
        } else {
            const defaultZoomOption = "website_sale.product_picture_magnify_click";
            await this._customizeWebsiteData(defaultZoomOption, { possibleValues: zoomOption._methodsParams.optionsPossibleValues["customizeWebsiteViews"] }, true);
            updateWidth();
        }
    },

    /**
     * @override
     */
    async setImageLayout(previewMode, widgetValue, params) {
        const zoomOption = this._getZoomOptionData();
        const updateLayout = this._updateWebsiteConfig.bind(this, { product_page_image_layout: widgetValue });
        if (!zoomOption) {
            updateLayout();
        } else {
            const imageWidthOption = this.productDetailMain.dataset.image_width;
            let defaultZoomOption = widgetValue === "grid" ? "website_sale.product_picture_magnify_click" : "website_sale.product_picture_magnify_hover";
            if (imageWidthOption === "100_pc" && defaultZoomOption === "website_sale.product_picture_magnify_hover") {
                defaultZoomOption = "website_sale.product_picture_magnify_click";
            }
            await this._customizeWebsiteData(defaultZoomOption, { possibleValues: zoomOption._methodsParams.optionsPossibleValues["customizeWebsiteViews"] }, true);
            updateLayout();
        }
    },

    /**
     * Emulate click on the main image of the carousel.
     */
    replaceMainImage: function () {
        const image = this.productDetailMain.querySelector(`[data-oe-model="${this.mode}"][data-oe-field=image_1920] img`);
        image.dispatchEvent(new Event('dblclick', {bubbles: true}));
    },

    _getSelectedVariantValues($container) {
        const combination = $container.find('input.js_product_change:checked').data('combination');

        if (combination) {
            return combination;
        }
        const values = [];

        const variantsValuesSelectors = [
            'input.js_variant_change:checked',
            'select.js_variant_change'
        ];
        _.each($container.find(variantsValuesSelectors.join(', ')), function (el) {
            values.push(+$(el).val());
        });

        return values;
    },

    /**
     * Prompts the user for images, then saves the new images.
     */
    addImages: function () {
        if(this.mode === 'product.template'){
            this.displayNotification({
                type: 'info',
                message: 'Pictures will be added to the main image. Use "Instant" attributes to set pictures on each variants'
            });
        }
        const dialog = new ComponentWrapper(this, AttachmentMediaDialogWrapper, {
            multiImages: true,
            onlyImages: true,
            save: attachments => {
                this._rpc({
                    route: `/shop/product/extra-images`,
                    params: {
                        images: attachments,
                        product_product_id: this.productProductID,
                        product_template_id: this.productTemplateID,
                        combination_ids: this._getSelectedVariantValues(this.$target.find('.js_add_cart_variants')),
                    }
                }).then(() => {
                    this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector});
                });
            }
        });
        dialog.mount(document.body);
    },

    /**
     * Removes all extra-images from the product.
     */
    clearImages: function () {
        this._rpc({
            route: `/shop/product/clear-images`,
            params: {
                model: this.mode,
                product_product_id: this.productProductID,
                product_template_id: this.productTemplateID,
                combination_ids: this._getSelectedVariantValues(this.$target.find('.js_add_cart_variants')),
            }
        }).then(() => {
            this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector});
        });
    },

    /**
     * @override
     */
    setSpacing(previewMode, widgetValue, params) {
        const spacing = {
            0: 'none',
            1: 'small',
            2: 'medium',
            3: 'big',
        }[widgetValue];
        this._rpc({
            route: '/shop/config/website',
            params: {
                'product_page_image_spacing': spacing,
            },
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector}));
        this.productPageGrid.dataset.image_spacing = spacing;
    },

    setColumns(previewMode, widgetValue, params) {
        this._rpc({
            route: '/shop/config/website',
            params: {
                'product_page_grid_columns': widgetValue,
            },
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector}));
        this.productPageGrid.dataset.grid_columns = widgetValue;
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'setImageWidth':
                return this.productDetailMain.dataset.image_width;
            case 'setImageLayout':
                return this.productDetailMain.dataset.image_layout;
            case 'setSpacing':
                if (!this.productPageGrid) return 0;
                return {
                    'none': 0,
                    'small': 1,
                    'medium': 2,
                    'big': 3,
                }[this.productPageGrid.dataset.image_spacing];
            case 'setColumns':
                return this.productPageGrid && this.productPageGrid.dataset.grid_columns || 1;
        }
        return this._super(...arguments);
    },

    async _computeWidgetVisibility(widgetName, params) {
        const hasImages = this.productDetailMain.dataset.image_width != 'none';
        const isFullImage = this.productDetailMain.dataset.image_width == '100_pc';
        switch (widgetName) {
            case 'o_wsale_thumbnail_pos':
                return Boolean(this.productPageCarousel) && hasImages;
            case 'o_wsale_grid_spacing':
            case 'o_wsale_grid_columns':
                return Boolean(this.productPageGrid) && hasImages;
            case 'o_wsale_image_layout':
            case 'o_wsale_zoom_click':
            case 'o_wsale_zoom_none':
            case 'o_wsale_replace_main_image':
            case 'o_wsale_add_extra_images':
            case 'o_wsale_clear_extra_images':
            case 'o_wsale_zoom_mode':
                return hasImages;
            case 'o_wsale_zoom_hover':
            case 'o_wsale_zoom_both':
                return hasImages && !isFullImage;
        }
        return this._super(widgetName, params);
    }
});

options.registry.WebsiteSaleProductAttribute = options.Class.extend({
    /**
     * @override
     */
     willStart: async function () {
        this.attributeID = this.$target.closest('[data-attribute_id]').data('attribute_id');
        return this._super(...arguments);
    },

    /**
     * @see this.selectClass for params
     */
    setDisplayType: function (previewMode, widgetValue, params) {
        this._rpc({
            route: '/shop/config/attribute',
            params: {
                attribute_id: this.attributeID,
                display_type: widgetValue,
            },
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector}));
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'setDisplayType':
                return this.$target.closest('[data-attribute_display_type]').data('attribute_display_type');
        }
        return this._super(methodName, params);
    },
});

// Disable "Shown on Mobile" option if for dynamic product snippets
options.registry.MobileVisibility.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeVisibility() {
        return await this._super(...arguments)
            && !this.$target.hasClass('s_dynamic_snippet_products');
    },
});

// Disable save for alternative products snippet
options.registry.SnippetSave.include({
    /**
     * @override
     */
    async _computeVisibility() {
        return await this._super(...arguments)
            && !this.$target.hasClass('o_wsale_alternative_products');
    }
});

options.registry.ReplaceMedia.include({
    /**
     * @override
     */
    async willStart() {
        const parent = this.$target.parent();
        this.isProductPageImage = this.$target.closest('.o_wsale_product_images').length > 0;
        // Product Page images may be the product's image or a record of `product.image`
        this.recordModel = parent.data('oe-model');
        this.recordId = parent.data('oe-id');
        return this._super(...arguments);
    },
    /**
     * Removes the image in the back-end
     */
    async removeMedia() {
        this._rpc({
            route: '/shop/product/remove-image',
            params: {
                image_res_model: this.recordModel,
                image_res_id: this.recordId,
            },
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: '#product_detail_main'}));
    },
    /**
     * Change sequence of product page images
     * 
     */
    async setPosition(previewMode, widgetValue, params) {
        this._rpc({
            route: '/shop/product/resequence-image',
            params: {
                image_res_model: this.recordModel,
                image_res_id: this.recordId,
                move: widgetValue,
            },
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: '#product_detail_main'}));
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (['media_wsale_resequence', 'media_wsale_remove'].includes(widgetName)) {
            // Only include these if we are inside of the product's page images
            return this.isProductPageImage;
        }
        return this._super(...arguments);
    }
});

});

