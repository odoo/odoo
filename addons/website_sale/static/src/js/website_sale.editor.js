/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import "@website/js/editor/snippets.options";
import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { useChildSubEnv } from "@odoo/owl";
import weUtils from '@web_editor/js/common/utils';

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
        const PPG_LIMIT = 10000;
        const ppg = parseInt(widgetValue);
        if (!ppg || ppg < 1) {
            return false;
        }
        this.ppg = Math.min(ppg, PPG_LIMIT);
        return rpc('/shop/config/website', { 'shop_ppg': this.ppg });
    },
    /**
     * @see this.selectClass for params
     */
    setPpr: function (previewMode, widgetValue, params) {
        this.ppr = parseInt(widgetValue);
        return rpc('/shop/config/website', { 'shop_ppr': this.ppr });
    },
    /**
     * @see this.selectClass for params
     */
    setGap: function (previewMode, widgetValue, params) {
        this.gap = widgetValue;
        return rpc('/shop/config/website', { 'shop_gap': this.gap });
    },
    /**
     * @see this.selectClass for params
     */
    setDefaultSort: function (previewMode, widgetValue, params) {
        this.default_sort = widgetValue;
        return rpc('/shop/config/website', { 'shop_default_sort': this.default_sort });
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
    events: Object.assign({}, options.Class.prototype.events || {}, {
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
        this.defaultSort = this.$target[0].closest('[data-default-sort]').dataset.defaultSort
        this.productTemplateID = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));
        this.ribbonPositionClasses = {'left': 'o_ribbon_left', 'right': 'o_ribbon_right'};
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
        this.$ribbon.text(_t('Ribbon Name'));
        this.$ribbon.addClass('o_ribbon_left');
        this.ribbonEditMode = true;
        await this._saveRibbon(true);
    },
    /**
     * @see this.selectClass for params
     */
    async deleteRibbon(previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            this.dialog.add(ConfirmationDialog, {
                body: _t('Are you sure you want to delete this ribbon?'),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
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
    async setRibbonName(previewMode, widgetValue, params) {
        this.$ribbon.text(widgetValue.substring(0, 20)); // The maximum length is 20.
        if (!previewMode) {
            await this._saveRibbon();
        }
    },
    /**
     * @see this.selectClass for params
     */
    async setRibbonPosition(previewMode, widgetValue, params) {
        this.$ribbon[0].className = this.$ribbon[0].className.replace(
            /o_ribbon_(left|right)/, this.ribbonPositionClasses[widgetValue]
        );
        await this._saveRibbon();
    },
    /**
     * @see this.selectClass for params
     */
    changeSequence: function (previewMode, widgetValue, params) {
        return rpc('/shop/config/product', {
            product_id: this.productTemplateID,
            sequence: widgetValue,
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

        let sizeX = parseInt(this.$target[0].dataset.colspan || 1);
        let sizeY = parseInt(this.$target[0].dataset.rowspan || 1);

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
            $select.append(renderToElement('website_sale.ribbonSelectItem', {
                ribbon,
                isLeft: ribbon.position === 'left',
                textColor: ribbon.text_color || defaultTextColor,
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
            case 'setRibbonName':
                return this.$ribbon.text();
            case 'setRibbonPosition': {
                if (classList.contains('o_ribbon_left')) {
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
        const isDefaultSortFeatured = this.defaultSort === 'website_sequence asc';

        if (widgetName === 'create_ribbon_opt') {
            return !this.ribbonEditMode;
        } else if (widgetName === 'o_wsale_change_sequence_widget'){
            return isDefaultSortFeatured;
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
        const text = this.$ribbon.text().trim();
        const ribbon = {
            'name': text,
            'bg_color': this.$ribbon[0].style.backgroundColor,
            'text_color': this.$ribbon[0].style.color,
            'position': (this.$ribbon.attr('class').includes('o_ribbon_left')) ? 'left' : 'right',
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
        const ribbon = (
            this.ribbons[ribbonId] ||
            {name: '', bg_color: '', text_color: '', position: 'left'}
        );
        // This option also manages other products' ribbon, therefore we need a
        // way to access all of them at once. With the content being in an iframe,
        // this is the simplest way.
        const $editableDocument = $(this.$target[0].ownerDocument.body);
        const $ribbons = $editableDocument.find(`[data-ribbon-id="${ribbonId}"] .o_ribbon`);
        $ribbons.empty().append(ribbon.name);
        let htmlClasses;
        this.trigger_up('get_ribbon_classes', {callback: classes => htmlClasses = classes});
        $ribbons.removeClass(htmlClasses);

        $ribbons.addClass(this.ribbonPositionClasses[ribbon.position]);
        $ribbons.css('background-color', ribbon.bg_color || '');
        $ribbons.css('color', ribbon.text_color || '');

        if (!this.ribbons[ribbonId]) {
            $editableDocument.find(`[data-ribbon-id="${ribbonId}"]`).each((index, product) => delete product.dataset.ribbonId);
        }

        // The ribbon does not have a savable parent, so we need to trigger the
        // saving process manually by flagging the ribbon as dirty.
        this.$ribbon.addClass('o_dirty');
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
        // TODO this should be awaited somehow
        rpc('/shop/config/product', {
            product_id: this.productTemplateID,
            x: x,
            y: y,
        }).then(() => this._reloadEditable());
    },
    _reloadEditable() {
        return this.trigger_up('request_save', {reload: true, optionSelector: `.oe_product:has(span[data-oe-id=${this.productTemplateID}])`});
    }
});

// Small override of the MediaDialog to retrieve the attachment ids instead of img elements
class AttachmentMediaDialog extends MediaDialog {
    setup() {
        super.setup();
        useChildSubEnv({ addFieldImage: true });
    }
    /**
     * @override
     */
    async save() {
        await super.save();
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        if (selectedMedia.length) {
            await this.props.extraImageSave(selectedMedia);
        }
        this.props.close();
    }
}

options.registry.WebsiteSaleProductPage = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
    },

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

    /**
     * If an accordion is displayed in the product details, remove the classes that Bootstrap adds
     * when editing an accordion-item to avoid saving the template with the accordion opened.
     *
     * @override
     */
    async cleanForSave() {
        const accordionEl = this.productDetailMain.querySelector('#product_accordion');
        if (!accordionEl) return;

        const accordionItemsEls = accordionEl.querySelectorAll('.accordion-item');
        accordionItemsEls.forEach((item, key) => {
            const accordionButtonEl = item.querySelector('.accordion-button');
            const accordionCollapseEl = item.querySelector('.accordion-collapse');
            if (key !== 0 && accordionCollapseEl.classList.contains('show')) {
                accordionButtonEl.classList.add('collapsed');
                accordionButtonEl.setAttribute('aria-expanded', 'false');
                accordionCollapseEl.classList.remove('show');
            }
        });
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
        if (zoomOption && widgetValue === "100_pc") {
            const defaultZoomOption = "website_sale.product_picture_magnify_click";
            await this._customizeWebsiteData(defaultZoomOption, { possibleValues: zoomOption._methodsParams.optionsPossibleValues["customizeWebsiteViews"] }, true);
        }
        return rpc('/shop/config/website', { product_page_image_width: widgetValue });
    },

    /**
     * @override
     */
    async setImageLayout(previewMode, widgetValue, params) {
        const zoomOption = this._getZoomOptionData();
        if (zoomOption) {
            const imageWidthOption = this.productDetailMain.dataset.image_width;
            let defaultZoomOption = widgetValue === "grid" ? "website_sale.product_picture_magnify_click" : "website_sale.product_picture_magnify_hover";
            if (imageWidthOption === "100_pc" && defaultZoomOption === "website_sale.product_picture_magnify_hover") {
                defaultZoomOption = "website_sale.product_picture_magnify_click";
            }
            await this._customizeWebsiteData(defaultZoomOption, { possibleValues: zoomOption._methodsParams.optionsPossibleValues["customizeWebsiteViews"] }, true);
        }
        return rpc('/shop/config/website', { product_page_image_layout: widgetValue });
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
        $container
            .find(variantsValuesSelectors.join(", "))
            .toArray()
            .forEach((el) => {
                values.push(+$(el).val());
            });

        return values;
    },

    /**
     * Prompts the user for images, then saves the new images.
     */
    addImages: function () {
        if(this.mode === 'product.template'){
            this.notification.add(
                'Pictures will be added to the main image. Use "Instant" attributes to set pictures on each variants',
                { type: 'info' }
            );
        }
        let extraImageEls;
        this.call("dialog", "add", AttachmentMediaDialog, {
            multiImages: true,
            onlyImages: true,
            // Kinda hack-ish but the regular save does not get the information we need
            save: async (imgEls) => {
                extraImageEls = imgEls;
            },
            extraImageSave: async (attachments) => {
                for (const index in attachments) {
                    const attachment = attachments[index];
                    if (attachment.mimetype.startsWith("image/")) {
                        if (["image/gif", "image/svg+xml"].includes(attachment.mimetype)) {
                            continue;
                        }
                        await this._convertAttachmentToWebp(attachment, extraImageEls[index]);
                    }
                }
                rpc(`/shop/product/extra-images`, {
                    images: attachments,
                    product_product_id: this.productProductID,
                    product_template_id: this.productTemplateID,
                    combination_ids: this._getSelectedVariantValues(this.$target.find('.js_add_cart_variants')),
                }).then(() => {
                    this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector});
                });
            }
        });
    },

    async _convertAttachmentToWebp(attachment, imageEl) {
        // This method is widely adapted from onFileUploaded in ImageField.
        // Upon change, make sure to verify whether the same change needs
        // to be applied on both sides.
        if (await weUtils.isImageCorsProtected(imageEl)) {
            // The image is CORS protected; do not transform it into webp
            return;
        }
        // Generate alternate sizes and format for reports.
        const imgEl = document.createElement("img");
        imgEl.src = imageEl.src;
        await new Promise(resolve => imgEl.addEventListener("load", resolve));
        const originalSize = Math.max(imgEl.width, imgEl.height);
        const smallerSizes = [1024, 512, 256, 128].filter(size => size < originalSize);
        const webpName = attachment.name.replace(/\.(jpe?g|png)$/i, ".webp");
        let referenceId = undefined;
        for (const size of [originalSize, ...smallerSizes]) {
            const ratio = size / originalSize;
            const canvas = document.createElement("canvas");
            canvas.width = imgEl.width * ratio;
            canvas.height = imgEl.height * ratio;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "rgb(255, 255, 255)";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(imgEl, 0, 0, imgEl.width, imgEl.height, 0, 0, canvas.width, canvas.height);
            const [resizedId] = await this.orm.call("ir.attachment", "create_unique", [[{
                name: webpName,
                description: size === originalSize ? "" : `resize: ${size}`,
                datas: canvas.toDataURL("image/webp", 0.75).split(",")[1],
                res_id: referenceId,
                res_model: "ir.attachment",
                mimetype: "image/webp",
            }]]);
            if (size === originalSize) {
                attachment.original_id = attachment.id;
                attachment.id = resizedId;
                attachment.image_src = `/web/image/${resizedId}-autowebp/${attachment.name}`;
                attachment.mimetype = "image/webp";
            }
            referenceId = referenceId || resizedId; // Keep track of original.
            await this.orm.call("ir.attachment", "create_unique", [[{
                name: webpName.replace(/\.webp$/, ".jpg"),
                description: "format: jpeg",
                datas: canvas.toDataURL("image/jpeg", 0.75).split(",")[1],
                res_id: resizedId,
                res_model: "ir.attachment",
                mimetype: "image/jpeg",
            }]]);
        }
    },

    /**
     * Removes all extra-images from the product.
     */
    clearImages: function () {
        return rpc(`/shop/product/clear-images`, {
            model: this.mode,
            product_product_id: this.productProductID,
            product_template_id: this.productTemplateID,
            combination_ids: this._getSelectedVariantValues(this.$target.find('.js_add_cart_variants')),
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
        this.productPageGrid.dataset.image_spacing = spacing;

        return rpc('/shop/config/website', {
            'product_page_image_spacing': spacing,
        });
    },

    setColumns(previewMode, widgetValue, params) {
        this.productPageGrid.dataset.grid_columns = widgetValue;
        return rpc('/shop/config/website', {
            'product_page_grid_columns': widgetValue,
        });
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
        const multipleImages = hasImages && this.productDetailMain.querySelector(
            '.o_wsale_product_images'
        ).dataset.imageAmount > 1;
        const isGrid = !!this.productDetailMain.querySelector('#o-grid-product');
        switch (widgetName) {
            case 'o_wsale_thumbnail_pos':
                return Boolean(this.productPageCarousel) && hasImages;
            case 'o_wsale_grid_spacing':
                return isGrid && multipleImages;
            case 'o_wsale_grid_columns':
                return Boolean(this.productPageGrid) && hasImages && isGrid && multipleImages;
            case 'o_wsale_image_layout':
                return multipleImages;
            case "o_wsale_image_ratio":
                return !isGrid && multipleImages;
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
        return rpc('/shop/config/attribute', {
            attribute_id: this.attributeID,
            display_type: widgetValue,
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
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },
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
        if (this.recordModel === "product.image") {
            // Unlink the "product.image" record as it is not the main product
            // image.
            await this.orm.unlink("product.image", [this.recordId]);
        }
        this.$target[0].remove();
        this.trigger_up("request_save", {reload: true, optionSelector: "#product_detail_main"});
    },
    /**
     * Change sequence of product page images
     *
     */
    async setPosition(previewMode, widgetValue, params) {
        return rpc('/shop/product/resequence-image', {
            image_res_model: this.recordModel,
            image_res_id: this.recordId,
            move: widgetValue,
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

options.registry.ImageTools.include({

    /**
     * @override
     */
    _computeMaxDisplayWidth() {
        const img = this._getImg();

        this._super(...arguments);
        // If the image is within an element with class '.o_img_with_max_suggested_width', set its
        // width to MAX_SUGGESTED_WIDTH. This ensures the zoom feature works on product images,
        // addressing the issue where optimized images couldn't be zoomed.
        if (img.closest('[name="o_img_with_max_suggested_width"]')) {
            return Math.round(this.MAX_SUGGESTED_WIDTH);
        }
    },

});
