odoo.define('stock.stock_move_forecast_qweb', function (require) {
"use strict";

var QwebView = require('web.qweb');
var registry = require('web.view_registry');

// New renderer to use draggable
var QwebRenderer = QwebView.Renderer.extend({
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var unfold_product_ids = [];
            $('.fa-minus-square').each(function (idx, value) {
                unfold_product_ids.push(parseInt($(this).parents('.row').attr('data-product-id')));
            });
            self.$('.collapse-button').click(function() {
                var productId = parseInt($(this).parents('.row').attr('data-product-id'));
                if ($(this).hasClass('fa-plus-square')) {
                    if (unfold_product_ids.indexOf(productId) === -1) {
                        unfold_product_ids.push(productId);
                    }
                } else {
                    if (unfold_product_ids.indexOf(productId) > -1) {
                        unfold_product_ids.splice(unfold_product_ids.indexOf(productId), 1 );
                    }
                }
                $(this).toggleClass('fa-plus-square');
                $(this).toggleClass('fa-minus-square')
            });

            self.$('.o_move').draggable({
                helper: 'clone',
                opacity: 0.4,
                scroll: false,
                revert: 'invalid',
                revertDuration: 200,
                refreshPositions: true,
                start: function (e, ui) {
                    self.$(e.target).parents('.col-droppable').droppable('disable');
                    ui.helper.data(self.$el.data());
                    ui.helper.addClass("ui-draggable-helper");
                },
                stop: function (e, ui) {
                    self.$(e.target).parents('.col-droppable').droppable('enable');
                }
            });
            self.$('.col-droppable').droppable({
                accept: function (d) {
                    var currentProductId = this.parentElement.dataset['productId'];
                    if(d.hasClass('o_product_' + currentProductId)) {
                        return true;
                    }
                },
                activeClass: 'o_stock_forecast_droppable_active',
                hoverClass: 'o_stock_forecast_droppable_hover',
                drop: function (e, ui) {
                    var $moveCell = ui.draggable;
                    var targetCol = e.target;
                    var move_id = parseInt($moveCell.attr('data-move-id'));
                    var dateIdx = parseInt(targetCol.dataset['dateIdx']);
                    var header = self.$('.col-header')[dateIdx - 1];
                    console.log(unfold_product_ids);
                    self._rpc({
                        model: 'stock.move',
                        method: 'reschedule',
                        args: [move_id, {
                            'date_expected': header.dataset['date'],
                            'unfold_product_ids': unfold_product_ids,
                        }],
                    }).then( function (action) {
                        self.do_action(action);
                    });
                }
            });
        });
    },
});


var QWebView = QwebView.View.extend({
    searchMenuTypes: ['filter'],
    config: {
        Model: QwebView.Model,
        Renderer: QwebRenderer,
        Controller: QwebView.Controller,
    },
});

registry.add('stock_move_forecast_qweb', QWebView);

return {
    View: QWebView,
};

});
