odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var options = require('web_editor.snippets.options');
var weWidgets = require('web_editor.widget');

var _t = core._t;
var QWeb = core.qweb;

options.registry.product_catalog = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.productCatalog = _.pick(this.$target.data(), 'type', 'selection', 'product_ids', 'order', 'x', 'y', 'category_id');
        this._bindGridSizeEvents();
        this._setGridSize();
        return this._super.apply(this, arguments);
    },
    /**
     * Remove snippet body
     *
     * @override
     */
    cleanForSave: function () {
        this.$target.find('.container').remove();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
    * Allow to change grid size.
    */
    gridSize: function () {
        this._setGridSize();
        this._renderProducts();
    },
    /**
    * Allow to change products order.
    *
    * @see this.selectClass for parameters
    */
    order: function (previewMode, value) {
        this.productCatalog.order = value;
        this._renderProducts();
    },
    /**
    * Allow to change product selection.
    *
    * @see this.selectClass for parameters
    */
    selection: function (previewMode, value, $li) {
        switch (value) {
            case 'all':
                this.productCatalog.selection = value;
                this._renderProducts();
                break;
            case 'category':
                this._categorySelection();
                break;
            case 'manual':
                this._manualSelection();
                break;
        }
    },
    /**
     * Allows to change catalog type (Slider or Grid).
     *
     * @see this.selectClass for parameters
     */
    type: function (previewMode, value) {
        this.productCatalog.type = value;
        this._renderProducts();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Bind events for grid size option
     *
     * @private
     */
    _bindGridSizeEvents: function () {
        this.$el.on('mouseenter', 'ul[name="size"] table', function (ev) {
            $(ev.currentTarget).addClass('oe_hover');
        });
        this.$el.on('mouseleave', 'ul[name="size"] table', function (ev) {
            $(ev.currentTarget).removeClass('oe_hover');
        });
        this.$el.on('mouseover', 'ul[name="size"] td', function (ev) {
            var $td = $(ev.currentTarget);
            var $table = $td.closest('table');
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;

            var tr = [];
            for (var yi = 0; yi < y; yi++) {
                tr.push('tr:eq(' + yi + ')');
            }
            var $selectTableRow = $table.find(tr.join(','));
            var td = [];
            for (var xi = 0; xi < x; xi++) {
                td.push('td:eq(' + xi + ')');
            }
            var $selectTableData = $selectTableRow.find(td.join(','));
            $table.find('td').removeClass('select');
            $selectTableData.addClass('select');
        });
    },
    /**
     * Open dialog which allow user to set product category
     *
     * @private
     */
    _categorySelection: function () {
        var self = this;
        new ProductCategorySelectionDialog(this, this.productCatalog.category_id, function (categoryID) {
            self.productCatalog.category_id = parseInt(categoryID);
            self.productCatalog.selection = 'category';
            self._setActive();
            self._renderProducts();
        }).open();
    },
    /**
     * Open dialog which allow user to set products manually
     *
     * @private
     */
    _manualSelection: function () {
        var self = this;
        var productIDs = _.map(this.$target.find('.o-product-item'), function (el) {
            return $(el).data('product-id');
        });
        var maxSize = this.productCatalog.type === 'grid' ? this.productCatalog.x * this.productCatalog.y : 16;
        new ProductManualSelectionDialog(this, productIDs, maxSize, function (changedProductIDs) {
            self.productCatalog.product_ids = changedProductIDs;
            self.productCatalog.selection = 'manual';
            self._setActive();
            self._renderProducts();
        }).open();
    },
    /**
     * Render 'productCatalog' widget.
     *
     * @private
     */
    _renderProducts: function () {
        var self = this;
        _.each(this.productCatalog, function (value, key) {
            self.$target.attr('data-' + key, value);
            self.$target.data(key, value);
        });
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: this.$target,
            onSuccess: function () {
                self.$target.trigger('content_changed');
            }
        });
    },
    /**
     * - Activate options
     * - Hide grid size option if catalog is slider
     * - Hide order option if manual selection is activated
     *
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);
        this.$el.filter('.o_grid_size').toggle(this.productCatalog.type === 'grid');
        this.$el.filter('.o_order_by').toggle(this.productCatalog.selection !== 'manual');

        this.$el.find('li[data-type]').removeClass('active')
            .filter('li[data-type=' + this.productCatalog.type + ']').addClass('active');
        this.$el.find('li[data-selection]').removeClass('active')
            .filter('li[data-selection=' + this.productCatalog.selection + ']').addClass('active');
        this.$el.find('li[data-order]').removeClass('active')
            .filter('li[data-order=' + this.productCatalog.order + ']').addClass('active');
    },
    /**
     * Set activated grid size on table
     *
     * @private
     */
    _setGridSize: function () {
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            this.productCatalog.x = $td.index() + 1;
            this.productCatalog.y = $td.parent().index() + 1;
        }
        var x = this.productCatalog.x;
        var y = this.productCatalog.y;
        var $grid = this.$el.find('ul[name="size"]');
        var $selected = $grid.find('tr:eq(0) td:lt(' + x + ')');
        if (y >= 2) {
            $selected = $selected.add($grid.find('tr:eq(1) td:lt(' + x + ')'));
        }
        if (y >= 3) {
            $selected = $selected.add($grid.find('tr:eq(2) td:lt(' + x + ')'));
        }
        if (y >= 4) {
            $selected = $selected.add($grid.find('tr:eq(3) td:lt(' + x + ')'));
        }
        $grid.find('td').removeClass('selected');
        $selected.addClass('selected');
    },
});

/**
 * Dialog which allow user to select product category.
 */
var ProductCategorySelectionDialog = weWidgets.Dialog.extend({
    template: 'website_sale.product_category_selection_dialog',
    events : _.extend({}, weWidgets.Dialog.prototype.events, {
        'change [name="selection"]': '_onChangeSelection',
    }),
    /**
     * @constructor
     * @param {integer} categoryID category id
     * @param {function} saveCallback save callback function
     */
    init: function (parent, categoryID, saveCallback) {
        var self = this;
        this.categoryID = categoryID;
        this._super(parent, {
            title: _t("Select Product Category"),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary o_save_btn',
                    close: true,
                    click: function () {
                        saveCallback(self.$('[name="selection"]').val());
                    }
                },
                {
                    text: _t("Discard"),
                    close: true
                },
            ],
        });
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['name'],
        }).then(function (categories) {
            self.categories = categories;
        });
        return $.when(this._super.apply(this, arguments), def);
    },
    /**
     * Initialize select2
     *
     * @override
     */
    start: function () {
        this.$('[name="selection"]').select2({
            width: '70%',
            data: _.map(this.categories, function (category) {
                return {'id': category.id, 'text': category.name};
            }),
        });
        this.$footer.find('.o_save_btn').prop('disabled', true);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeSelection: function (ev) {
        var self = this;
        this._rpc({
            model: 'product.template',
            method: 'search_count',
            args: [[['public_categ_ids', 'child_of', [parseInt($(ev.currentTarget).val())]], ['website_published', '=', true]]]
        }).then(function (productsCount) {
            self.$('.o_alert').toggleClass('hidden', productsCount !== 0);
            self.$footer.find('.o_save_btn').prop('disabled', !productsCount);
        });
    },
});

/**
 * Dialog which allow user to select products manually.
 */
var ProductManualSelectionDialog = weWidgets.Dialog.extend({
    template: 'website_sale.product_manual_selection_dialog',
    events : _.extend({}, weWidgets.Dialog.prototype.events, {
        'change [name="selection"]': '_onChangeSelection',
    }),
    /**
     * @constructor
     * @param {Array} productIDs List of product ids
     * @param {integer} maxSize Maximum size allow to select product
     * @param {function} saveCallback save callback function
     */
    init: function (parent, productIDs, maxSize, saveCallback) {
        var self = this;
        this.productIDs = productIDs;
        this.maxSize = maxSize;
        this._super(parent, {
            title: _t("Select Products Manually"),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary o_save_btn',
                    close: true,
                    click: function () {
                        saveCallback(self.$('[name="selection"]').val());
                    }
                },
                {
                    text: _t("Discard"),
                    close: true
                },
            ],
        });
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: 'product.template',
            method: 'search_read',
            fields: ['name'],
            domain: [['website_published', '=', true]]
        }).then(function (products) {
            self.products = products;
        });
        return $.when(this._super.apply(this, arguments), def);
    },
    /**
     * Initialize select2 and make it sortable
     *
     * @override
     */
    start: function () {
        var self = this;
        this.$('[name="selection"]').select2({
            width: '100%',
            multiple: true,
            maximumSelectionSize: this.maxSize,
            data: _.map(this.products, function (product) {
                return {'id': product.id, 'text': product.name};
            }),
        });
        // Make select2 sortable
        this.$('[name="selection"]').select2('container').find('ul.select2-choices').sortable({
            containment: 'parent',
            start: function () {
                self.$('[name="selection"]').select2('onSortStart');
            },
            update: function () {
                self.$('[name="selection"]').select2('onSortEnd');
            }
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeSelection: function (ev) {
        this.$footer.find('.o_save_btn').prop('disabled', !this.$('[name="selection"]').val());
    },
});

});
