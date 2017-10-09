odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var productCatalog = require('website_sale.product_catalog');
var rpc = require('web.rpc');

var _t = core._t;
var QWeb = core.qweb;

options.registry.catalog = options.Class.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Initialize product catalog, set grid selection and bind grid option events.
     *
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        self = this;
        this.productCatalog = new productCatalog.ProductCatalog(this.$target);
        this._renderProductCatalog().then(function () {
            self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
        });
        this._setGrid();
        this._bindGridEvents();
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Bind events of grid option.
     *
     * @private
     */
    _bindGridEvents: function () {
        var self = this;
        this.$el.on('mouseenter', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).addClass('oe_hover');
        });
        this.$el.on('mouseleave', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).removeClass('oe_hover');
        });
        this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
            var $td = $(event.currentTarget);
            var $table = $td.closest('table');
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;

            var tr = [];
            for (var yi = 0; yi < y; yi++) {
                tr.push('tr:eq(' + yi + ')');
            }
            var $select_tr = $table.find(tr.join(','));
            var td = [];
            for (var xi = 0; xi < x; xi++) {
                td.push('td:eq(' + xi + ')');
            }
            var $select_td = $select_tr.find(td.join(','));
            $table.find('td').removeClass('select');
            $select_td.addClass('select');
        });
    },

    /**
     * Render product catalog widget.
     *
     * @private
     */
    _renderProductCatalog: function () {
        var self = this;
        this.$target.find('.s_no_resize_cols').remove();
        return this.productCatalog.appendTo(this.$target.find('.container')).then(function () {
            // cover the target element when dynamic grid size change.
            self.trigger_up('cover_update');
            // set default cursor in edit mode of snippet.
            self.$target.find('.product-image a, .product-details a, span.fa, i.fa').css('cursor', 'default');
            // prevent orignal events like add to cart etc in edit mode
            self.$target.find('.product-buttons a').on('click', function (event) {
                event.stopPropagation();
            });
        });
    },

    /**
     * Set selected size on grid option.
     *
     * @private
     */
    _setGrid: function () {
        var x = this.$target.data('x');
        var y = this.$target.data('y');
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
        $selected.addClass('selected');
    },

    /**
     * Select product catalog size.
     */
    size: function (type, value, $li) {
        if (!this.__click) {
            return;
        }
        var self = this;
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;
            this.$target.attr('data-x', x);
            this.$target.attr('data-y', y);

            if (this.$target.attr('data-selection') == "category") {
                this.productCatalog.options.domain = ['public_categ_ids', '=', parseInt(this.$target.attr('data-catagory-id'))];
            } else if (this.$target.attr('data-selection') == "manual") {
                var reorderIDs = this.$target.attr('data-reorder-ids');
                this.productCatalog.options.domain = ['id', 'in', reorderIDs.split(',')];
            } else {
                this.productCatalog.options.domain = [];
            }

            if (this.$target.attr('data-sortby') == "reorder_products") {
                this.productCatalog.options.sortby = this.productCatalog.sortBy['name_asc'];
            }

            this.productCatalog.options.size = this.productCatalog.sizes[x];
            this.productCatalog.options.limit = x * y;
            this._renderProductCatalog().then(function () {
                self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
            });
        }
    },

    /**
     * Select products.
     */
    selection: function (type, value, $li) {
        if (!this.__click) {
            return;
        }
        var self = this;
        if (this.$target.attr('data-sortby') == "reorder_products") {
            this.productCatalog.options.sortby = this.productCatalog.sortBy['name_asc'];
        }
        switch (value) {
            case 'all':
                this.$target.attr('data-selection', value);
                this.productCatalog.options.domain = [];
                this._renderProductCatalog().then(function () {
                    self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
                });
                break;
            case 'category':
                this.catagorySelection();
                break;
            case 'manual':
                this.manualSelection();
                break;
        }
    },

    /**
     * Select products catagory wise.
     */
    catagorySelection: function () {
        var self = this;
        rpc.query({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['id', 'name'],
        }).then(function (result) {
            var dialog = new Dialog(null, {
                title: _t('Select Product Category'),
                $content: $(QWeb.render('product_catalog.catagorySelection')),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        var categoryID = dialog.$content.find('[name="selection"]').val();
                        self.$target.attr('data-selection', 'category');
                        self.$target.attr('data-catagory-id', categoryID);

                        self.productCatalog.options.domain = ['public_categ_ids', 'child_of', [parseInt(categoryID)]];
                        self._renderProductCatalog().then(function () {
                            self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
                        });
                    }},
                    {text: _t('Discard'), close: true}
                ]
            });
            dialog.$content.find('[name="selection"]').val(self.$target.attr('data-catagory-id'));
            dialog.$content.find('[name="selection"]').select2({
                width: '70%',
                data: _.map(result, function (r) {
                    return {'id': r.id, 'text': r.name};
                }),
            });
            dialog.$content.find('[name="selection"]').change(function () {
                rpc.query({
                    model: 'product.template',
                    method: 'search_count',
                    args:[[['public_categ_ids', 'child_of', [parseInt($(this).val())]], ['website_published', '=', true]]]
                }).then(function (result) {
                    self.toggle_warning(dialog, result !== 0);
                });
            });
            dialog.open();
        });
    },

    /**
     * Select products manually.
     */
    manualSelection: function () {
        var self = this;
        rpc.query({
            model: 'product.template',
            method: 'search_read',
            fields: ['id', 'name'],
            domain: [['website_published', '=', true]]
        }).then(function (result) {
            var dialog = new Dialog(null, {
                title: _t('Select Product Manually'),
                $content: $(QWeb.render('product_catalog.manualSelection')),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        var productIDS = dialog.$content.find('[name="selection"]').val().split(',');
                        self.$target.attr('data-selection', 'manual');

                        self.productCatalog.options.domain = ['id', 'in', productIDS];
                        self._renderProductCatalog().then(function () {
                            self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
                        });
                    }},
                    {text: _t('Discard'), close: true}
                ]
            });
            dialog.$content.find('[name="selection"]').val(self.productCatalog._getProductIds());
            dialog.$content.find('[name="selection"]').select2({
                width: '100%',
                multiple: true,
                maximumSelectionSize: self.productCatalog.options.limit,
                data: _.map(result, function (r) {
                    return {'id': r.id, 'text': r.name};
                }),
            }).change(function () {
                if (dialog.$content.find('[name="selection"]').val() == "") {
                    dialog.$footer.find('.btn-primary').prop('disabled', true);
                } else {
                    dialog.$footer.find('.btn-primary').prop('disabled', false);
                }
            });
            dialog.open();
        });
    },

    /**
     * Apply sorting.
     */
    sortby: function (type, value, $li) {
        if (!this.__click) {
            return;
        }
        var self = this;
        if (value !== "reorder_products") {
            this.$target.attr('data-sortby', value);
            if (this.$target.attr('data-selection') == "manual") {
                var reorderIDs = this.$target.attr('data-reorder-ids');
                this.productCatalog.options.domain = ['id', 'in', reorderIDs.split(',')];
            } else if (this.$target.attr('data-selection') == "category") {
                this.productCatalog.options.domain = ['public_categ_ids', '=', parseInt(this.$target.attr('data-catagory-id'))];
            } else {
                this.productCatalog.options.domain = this.productCatalog.domains[this.$target.attr('data-selection')];
            }
            this.productCatalog.options.sortby = this.productCatalog.sortBy[value];
            this._renderProductCatalog().then(function () {
                self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
            });
        } else {
            var dialog = new Dialog(null, {
                title: _t('Drag a product to re-arrange display sequence'),
                $content: $(QWeb.render('product_catalog.reorderproducts.dialog', {'products': this.productCatalog.products})),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        var pIDs = [];
                        _.map(dialog.$content.find('ul.reorder_products > li'), function(el) {
                            pIDs.push($(el).data('menu-id').toString());
                        });
                        self.$target.attr('data-sortby', value);
                        self.productCatalog.options.domain = ['id', 'in', pIDs];
                        self.productCatalog.options.reorder_ids = pIDs.join(',');
                        self.productCatalog.options.sortby = self.productCatalog.sortBy[value];
                        self._renderProductCatalog().then(function () {
                            self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
                        });
                    }},
                    {text: _t('Discard'), close: true}
                ]
            });
            dialog.$content.find('.reorder_products').sortable();
            dialog.open();
        }
    },

    /**
     * If Selected catagory has no saleable products.
     * Then alert warning message and disabled save button.
     */
    toggle_warning: function(dialog, toggle) {
        dialog.$('.alert-info').toggleClass('hidden', toggle);
        dialog.$footer.find('.btn-primary').prop('disabled', !toggle);
    },

    /**
     * The set_active method tweaks the option dropdown to show the selected value
     * according to the state of the $target the option customizes.
     *
     * @override
     */
    set_active: function () {
        this._super.apply(this, arguments);
        this.$el.find('ul[name="selection"] li').removeClass('active')
            .filter('ul[name="selection"] li[data-selection="' + this.$target.attr('data-selection') + '"]').addClass('active');
        this.$el.find('ul[name="sortby"] li').removeClass('active')
            .filter('ul[name="sortby"] li[data-sortby="' + this.$target.attr('data-sortby') + '"]').addClass('active');
    }
});

});
