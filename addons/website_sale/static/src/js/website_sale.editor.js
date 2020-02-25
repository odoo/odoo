odoo.define('website_sale.add_product', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_product: '_createNewProduct',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new product to create, then creates it
     * and redirects the user to this new product.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewProduct: function () {
        var self = this;
        return wUtils.prompt({
            id: "editor_new_product",
            window_title: _t("New Product"),
            input: _t("Name"),
        }).then(function (result) {
            if (!result.val) {
                return;
            }
            return self._rpc({
                route: '/shop/add_product',
                params: {
                    name: result.val,
                },
            }).then(function (url) {
                window.location.href = url;
                return new Promise(function () {});
            });
        });
    },
});
});

//==============================================================================

odoo.define('website_sale.editor', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var publicWidget = require('web.public.widget');
var editorMenu = require('website.editor.menu');

var _t = core._t;
var qweb = core.qweb;
var showConfirmDialog = true;

publicWidget.registry.websiteSaleCurrency = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    disabledInEditableMode: false,
    edit_events: {
        'click .oe_currency_value:o_editable': '_onCurrencyValueClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCurrencyValueClick: function (ev) {
        $(ev.currentTarget).selectContent();
    },
});

var shopGridOptionsCommon = {
    /**
     * Displays confirmation dialog  if the user tries to change product grid.
     *
     * @private
     * @param {function} callback - the action to do on dialog confirmation
     * @returns {Promise}
     */
    _confirmWithDialogThen: function (callback) {
        var self = this;

        function doThenUpdateShopGrid() {
            return Promise.resolve(callback.call(self)).then(function () {
                self.trigger_up('deactivate_snippet');
                return self._updateShopGrid();
            });
        }

        return new Promise(function (resolve, reject) {
            if (showConfirmDialog) {
                Dialog.confirm(this, undefined, {
                    $content: $(qweb.render('website_sale.dialog_confirmation')),
                    'confirm_callback': function () {
                        showConfirmDialog = !this.$('#dialogShow').is(":checked");
                        return doThenUpdateShopGrid().then(resolve).guardedCatch(reject);
                    },
                    'cancel_callback': resolve,
                });
            } else {
                doThenUpdateShopGrid().then(resolve).guardedCatch(reject);
            }
        });
    },
    /**
     * @private
     * @param {jQuery} $productGrid
     */
    _getShopContext: function ($productGrid) {
        return _.pick($productGrid.children('.table').data(), function (value) {
            return _.isNumber(value) || _.isString(value);
        });
    },
    /**
     * @private
     */
    _updateShopGrid: function () {
        var self = this;
        var $productGrid = this.$target.closest('#wsale_product_grid');
        return this._rpc({
            route: '/shop/render_grid',
            params: {
                'shop_context': this._getShopContext($productGrid),
            },
        }).then(function (grid_body) {
            var $shopGrid = $(grid_body);
            self.trigger_up('force_destroy', {
                $el: $productGrid
            });
            self.trigger_up('make_editable', {
                $el: $shopGrid,
                reloadOnCancel: true,
            });
            $productGrid.replaceWith($shopGrid);
        });
    }
};

options.registry.WebsiteSaleGridLayout = options.Class.extend(shopGridOptionsCommon, {
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],

    /**
     * @override
     */
    start: function () {
        this.ppg = parseInt(this.$target.closest('[data-ppg]').data('ppg'));
        this.ppr = parseInt(this.$target.closest('[data-ppr]').data('ppr'));
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
        return this._confirmWithDialogThen(() => {
            return this._rpc({
                route: '/shop/change_ppg',
                params: {
                    'ppg': this.ppg,
                },
            });
        });
    },
    /**
     * @see this.selectClass for params
     */
    setPpr: function (previewMode, widgetValue, params) {
        this.ppr = parseInt(widgetValue);
        return this._confirmWithDialogThen(() => {
            return this._rpc({
                route: '/shop/change_ppr',
                params: {
                    'ppr': this.ppr,
                },
            })
        });
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
        }
        return this._super(...arguments);
    },
});

options.registry.WebsiteSaleProductsItem = options.Class.extend(shopGridOptionsCommon, {
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],
    events: _.extend({}, options.Class.prototype.events || {}, {
        'mouseenter .o_wsale_soptions_menu_sizes table': '_onTableMouseEnter',
        'mouseleave .o_wsale_soptions_menu_sizes table': '_onTableMouseLeave',
        'mouseover .o_wsale_soptions_menu_sizes td': '_onTableItemMouseEnter',
        'click .o_wsale_soptions_menu_sizes td': '_onTableItemClick',
    }),

    /**
     * @override
     */
    willStart: function () {
        this.ppr = this.$target.closest('[data-ppr]').data('ppr');
        this.productTemplateID = parseInt(this.$target.find('[data-oe-model="product.template"]').data('oe-id'));

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        var listLayoutEnabled = this.$target.closest('#products_grid').hasClass('o_wsale_layout_list');
        this.$el.find('.o_wsale_soptions_menu_sizes')
            .toggleClass('d-none', listLayoutEnabled);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    style: function (previewMode, widgetValue, params) {
        this._rpc({
            route: '/shop/change_styles',
            params: {
                'id': this.productTemplateID,
                'style_id': params.possibleValues[params.possibleValues.length - 1],
            },
        });
    },
    /**
     * @see this.selectClass for params
     */
    changeSequence: function (previewMode, widgetValue, params) {
        return this._confirmWithDialogThen(() => {
            return this._rpc({
                route: '/shop/change_sequence',
                params: {
                    id: this.productTemplateID,
                    sequence: widgetValue
                },
            });
        });
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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomWidgets: async function (uiFragment) {
        const checkboxes = [];
        return this._rpc({
            model: 'product.style',
            method: 'search_read',
        }).then(async data => {
            for (var k in data) {
                const checkboxWidget = this._registerUserValueWidget('we-checkbox', this, data[k]['name'], {
                    dataAttributes: {
                        'style': data[k]['id'],
                        'selectClass': data[k]['html_class'],
                    },
                });
                checkboxes.push(checkboxWidget);
                await checkboxWidget.appendTo(document.createDocumentFragment());
            }
        }).then(() => {
            const menuEl = uiFragment.querySelector('[name="style"]');
            for (const checkbox of checkboxes) {
                menuEl.appendChild(checkbox.el);
            }
        });
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
        var y = $td.parent().index() + 1;
        return this._confirmWithDialogThen(function () {
            return this._rpc({
                route: '/shop/change_size',
                params: {
                    id: this.productTemplateID,
                    x: x,
                    y: y,
                },
            });
        });
    },
});

/**
 * Handles the edition of products search bar snippet.
 */
options.registry.ProductsSearchBar = options.Class.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],

    /**
     * @override
     */
    start: function () {
        this.$searchProductsInput = this.$('.search-query');
        this.$searchOrderField = this.$('.o_wsale_search_order_by');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    openSearchbarSettings: function (previewMode, widgetValue, params) {
        var self = this;
        new Dialog(this, {
            title: _t("Products Search Bar"),
            $content: $(qweb.render('website_sale.dialog.productsSearchBar', {
                currentOrderBy: this.$searchOrderField.val(),
                currentLimit: parseInt(this.$searchProductsInput.attr('data-limit')),
                currentDisplayDescription: this.$searchProductsInput.attr('data-display-description') === 'true',
                currentDisplayPrice: this.$searchProductsInput.attr('data-display-price') === 'true',
                currentDisplayImage: this.$searchProductsInput.attr('data-display-image') === 'true',
            })),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    click: function () {
                        self.$searchOrderField.attr({
                            'value': this.$('#order_by').val(),
                        });
                        self.$searchProductsInput.attr({
                            'data-limit': this.$('#use_autocomplete').is(':checked') ? this.$('#limit').val() : 0,
                            'data-display-description': this.$('#display_description').is(':checked'),
                            'data-display-price': this.$('#display_price').is(':checked'),
                            'data-display-image': this.$('#display_image').is(':checked'),
                        });
                        self.$target.trigger('content_changed');
                        this.close();
                    },
                },
                {
                    text: _t("Discard"),
                    close: true,
                },
            ],
        }).open();
    },
});

editorMenu.include({
    custom_events: _.extend({}, editorMenu.prototype.custom_events || {}, {
        'make_editable': '_onMakeEditable',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    cancel: function (reload) {
        return this._super(this.reloadOnCancel || reload);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     */
    _onMakeEditable: function (ev) {
        var $el = ev.data.$el;
        this.reloadOnCancel = ev.data.reloadOnCancel;
        this.editable($el).addClass('o_editable');
    },
});

});
