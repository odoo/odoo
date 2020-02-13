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

var options = require('web_editor.snippets.options');
var publicWidget = require('web.public.widget');

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

function reload() {
    if (window.location.href.match(/\?enable_editor/)) {
        window.location.reload();
    } else {
        window.location.href = window.location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
    }
}

options.registry.WebsiteSaleGridLayout = options.Class.extend({

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
        return this._rpc({
            route: '/shop/change_ppg',
            params: {
                'ppg': ppg,
            },
        }).then(() => reload());
    },
    /**
     * @see this.selectClass for params
     */
    setPpr: function (previewMode, widgetValue, params) {
        this.ppr = parseInt(widgetValue);
        this._rpc({
            route: '/shop/change_ppr',
            params: {
                'ppr': this.ppr,
            },
        }).then(reload);
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
        this._rpc({
            route: '/shop/change_sequence',
            params: {
                id: this.productTemplateID,
                sequence: widgetValue,
            },
        }).then(reload);
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
        this._rpc({
            route: '/shop/change_size',
            params: {
                id: this.productTemplateID,
                x: x,
                y: y,
            },
        }).then(reload);
    },
});
});
