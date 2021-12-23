odoo.define('product.generate_pricelist', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var FieldMany2One = require('web.relational_fields').FieldMany2One;
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var QtyTagWidget = Widget.extend({
    template: 'product.report_pricelist_qty',
    events: {
        'click .o_remove_qty': '_onClickRemoveQty',
    },
    /**
     * @override
     */
    init: function (parent, defaulQuantities) {
        this._super.apply(this, arguments);
        this.quantities = defaulQuantities;
        this.MAX_QTY = 5;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add a quantity when add(+) button clicked.
     *
     * @private
     */
    _onClickAddQty: function () {
        if (this.quantities.length >= this.MAX_QTY) {
            this.do_notify(false, _.str.sprintf(
                _t("At most %d quantities can be displayed simultaneously. Remove a selected quantity to add others."),
                this.MAX_QTY
            ));
            return;
        }
        const qty = parseInt(this.$('.o_product_qty').val());
        if (qty && qty > 0) {
            // Check qty already exist
            if (this.quantities.indexOf(qty) === -1) {
                this.quantities.push(qty);
                this.quantities = this.quantities.sort((a, b) => a - b);
                this.trigger_up('qty_changed', {quantities: this.quantities});
                this.renderElement();
            } else {
                this.displayNotification({
                    message: _.str.sprintf(_t("Quantity already present (%d)."), qty),
                    type: 'info'
                });
            }
        } else {
            this.do_notify(false, _t("Please enter a positive whole number"));
        }
    },
    /**
     * Remove quantity.
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickRemoveQty: function (ev) {
        const qty = parseInt($(ev.currentTarget).closest('.badge').data('qty'));
        this.quantities = this.quantities.filter(q => q !== qty);
        this.trigger_up('qty_changed', {quantities: this.quantities});
        this.renderElement();
    },
});

var GeneratePriceList = AbstractAction.extend(StandaloneFieldManagerMixin, {
    hasControlPanel: true,
    events: {
        'click .o_action': '_onClickAction',
        'submit form': '_onSubmitForm',
    },
    custom_events: Object.assign({}, StandaloneFieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
        qty_changed: '_onQtyChanged',
    }),
    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.context = params.context;
        // in case the window got refreshed
        if (params.params && params.params.active_ids && typeof(params.params.active_ids === 'string')) {
            try {
                this.context.active_ids = params.params.active_ids.split(',').map(id => parseInt(id));
                this.context.active_model = params.params.active_model;
            } catch(e) {
                console.log('unable to load ids from the url fragment 🙁');
            }
        }
        if (!this.context.active_model) {
            // started without an active module, assume product templates
            this.context.active_model = 'product.template';
        }
        this.context.quantities = [1, 5, 10];
    },
    /**
     * @override
     */
    willStart: function () {
        let getPricelit;
        // started without a selected pricelist in context? just get the first one
        if (this.context.default_pricelist) {
            getPricelit = Promise.resolve([this.context.default_pricelist]);
        } else {
            getPricelit = this._rpc({
                model: 'product.pricelist',
                method: 'search',
                args: [[]],
                kwargs: {limit: 1}
            })
        }
        const fieldSetup = getPricelit.then(pricelistIds => {
            return this.model.makeRecord('report.product.report_pricelist', [{
                name: 'pricelist_id',
                type: 'many2one',
                relation: 'product.pricelist',
                value: pricelistIds[0],
            }]);
        }).then(recordID => {
            const record = this.model.get(recordID);
            this.many2one = new FieldMany2One(this, 'pricelist_id', record, {
                mode: 'edit',
                attrs: {
                    can_create: false,
                    can_write: false,
                    options: {no_open: true},
                },
            });
            this._registerWidget(recordID, 'pricelist_id', this.many2one);
        });
        return Promise.all([fieldSetup, this._getHtml(), this._super()]);
    },
    /**
     * @override
     */
    start: function () {
        this.controlPanelProps.cp_content = this._renderComponent();
        return this._super.apply(this, arguments).then(() => {
            this.$('.o_content').html(this.reportHtml);
        });
    },
    /**
     * Include the current model (template/variant) in the state to allow refreshing without losing
     * the proper context.
     * @override
     */
    getState: function() {
        return {
            active_model: this.context.active_model,
        };
    },
    getTitle: function() {
        return _t('Pricelist Report');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get template to display report.
     *
     * @private
     * @returns {Promise}
     */
    _getHtml: function () {
        return this._rpc({
            model: 'report.product.report_pricelist',
            method: 'get_html',
            kwargs: {context: this.context},
        }).then(result => {
            this.reportHtml = result;
        });
    },
    /**
     * Reload report.
     *
     * @private
     * @returns {Promise}
     */
    _reload: function () {
        return this._getHtml().then(() => {
            this.$('.o_content').html(this.reportHtml);
        });
    },
    /**
     * Render search view and print button.
     *
     * @private
     */
    _renderComponent: function () {
        const $buttons = $('<button>', {
            class: 'btn btn-primary',
            text: _t("Print"),
        }).on('click', this._onClickPrint.bind(this));

        const $searchview = $(QWeb.render('product.report_pricelist_search'));
        this.many2one.appendTo($searchview.find('.o_pricelist'));

        this.qtyTagWidget = new QtyTagWidget(this, this.context.quantities);
        this.qtyTagWidget.replace($searchview.find('.o_product_qty'));
        return { $buttons, $searchview };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open form view of particular record when link clicked.
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickAction: function (ev) {
        ev.preventDefault();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(ev.currentTarget).data('model'),
            res_id: $(ev.currentTarget).data('res-id'),
            views: [[false, 'form']],
            target: 'self',
        });
    },
    /**
     * Print report in PDF when button clicked.
     *
     * @private
     */
    _onClickPrint: function () {
        const reportName = _.str.sprintf('product.report_pricelist?active_model=%s&active_ids=%s&pricelist_id=%s&quantities=%s',
            this.context.active_model,
            this.context.active_ids || '',
            this.context.pricelist_id || '',
            this.context.quantities.toString() || '1',
        );
        return this.do_action({
            type: 'ir.actions.report',
            report_type: 'qweb-pdf',
            report_name: reportName,
            report_file: 'product.report_pricelist',
        });
    },
    /**
     * Reload report when pricelist changed.
     *
     * @override
     */
    _onFieldChanged: function (event) {
        this.context.pricelist_id = event.data.changes.pricelist_id.id;
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        this._reload();
    },
    /**
     * Reload report when quantities changed.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer[]} event.data.quantities
     */
    _onQtyChanged: function (ev) {
        this.context.quantities = ev.data.quantities;
        this._reload();
    },
    _onSubmitForm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.qtyTagWidget._onClickAddQty();
    },
});

core.action_registry.add('generate_pricelist', GeneratePriceList);

return {
    GeneratePriceList,
    QtyTagWidget
};

});
