odoo.define('product_matrix.section_and_note_widget', function (require) {

var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;
var qweb = core.qweb;
var fieldRegistry = require('web.field_registry');
require('account.section_and_note_backend');

var SectionAndNoteFieldOne2Many = fieldRegistry.get('section_and_note_one2many');

SectionAndNoteFieldOne2Many.include({
    custom_events: _.extend({}, SectionAndNoteFieldOne2Many.prototype.custom_events, {
        open_matrix: '_openMatrix',
    }),

    /**
     * Sends the matrix modifications to the server
     * Through a change on an invisible non stored field.
     *
     * @param {List} list of changes in the matrix, to be applied to the order.
     *    {integer} quantity: float
     *    {List} ptav_ids: product.template.attribute.value ids
     *
     * @private
    */
    _applyGrid: function (changes, productTemplateId) {
        // the getParent is to trigger the event on the form Controller instead of the one2many.
        // If not, the one2many crashes on reset because it tries to find an operation in the event
        // even if there isn't any.
        // the only solution would be to use a custom event catched on a new controller
        // on the so/po form (as a js_class).
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                grid: JSON.stringify({changes: changes, product_template_id: productTemplateId}),
                grid_update: true // to say that the changes to grid have to be applied to the SO.
            },
            viewType: 'form',
        });
    },

    /**
     * Catches the event asking for matrix opening
     *
     * @param {OdooEvent} ev various values needed to open the matrix
     *  {integer} data.product_template_id product.template id
     *  {list} data.editedCellAttributes list of product.template.attribute.value ids
     *  {bool} data.edit whether the line source should be deleted or not.
     *
     * @private
    */
    _openMatrix: function (ev) {
        ev.stopPropagation();
        var self = this;
        var dataPointId = ev.data.dataPointId;
        var productTemplateId = ev.data.product_template_id;
        var editedCellAttributes = ev.data.editedCellAttributes;
        if (!ev.data.edit) {
            // remove the line used to open the matrix
            this._setValue({operation: 'DELETE', ids: [dataPointId]});
        }
        // the getParent is to trigger the event on the form Controller instead of the one2many.
        // If not, the one2many crashes on reset because it tries to find an operation in the event
        // even if there isn't any.
        // the only solution would be to use a custom event catched on a new controller
        // on the so/po form (as a js_class).
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                grid_product_tmpl_id: {id: productTemplateId}
            },
            viewType: 'form',
            onSuccess: function (result) {
                // result = list of widgets
                // find one of the SO widget
                // (not so lines because the grid values are computed on the SO)
                // and get the grid information from its recordData.
                var gridInfo = result.find(r => r.recordData.grid).recordData.grid;
                self._openMatrixConfigurator(gridInfo, productTemplateId, editedCellAttributes);
            }
        });
    },

    /**
     * Triggers Matrix Dialog opening
     *
     * @param {String} jsonInfo matrix dialog content
     * @param {integer} productTemplateId product.template id
     * @param {editedCellAttributes} list of product.template.attribute.value ids
     *  used to focus on the matrix cell representing the edited line.
     *
     * @private
    */
    _openMatrixConfigurator: function (jsonInfo, productTemplateId, editedCellAttributes) {
        var self = this;
        var infos = JSON.parse(jsonInfo);
        var MatrixDialog = new Dialog(this, {
            title: _t('Choose Product Variants'),
            size: 'extra-large', // adapt size depending on matrix size?
            $content: $(qweb.render(
                'product_matrix.matrix', {
                    header: infos.header,
                    rows: infos.matrix,
                }
            )),
            buttons: [
                {text: _t('Confirm'), classes: 'btn-primary', close: true, click: function (result) {
                    var $inputs = this.$('.o_matrix_input');
                    var matrixChanges = [];
                    _.each($inputs, function (matrixInput) {
                        if (matrixInput.value && matrixInput.value !== matrixInput.attributes.value.nodeValue) {
                            matrixChanges.push({
                                qty: parseFloat(matrixInput.value),
                                ptav_ids: matrixInput.attributes.ptav_ids.nodeValue.split(",").map(function (id) {
                                      return parseInt(id);
                                }),
                            });
                        }
                    });
                    if (matrixChanges.length > 0) {
                        self._applyGrid(matrixChanges, productTemplateId);
                    }
                }},
                {text: _t('Close'), close: true},
            ],
        }).open();

        MatrixDialog.opened(function () {
            if (editedCellAttributes.length > 0) {
                var str = editedCellAttributes.toString();
                MatrixDialog.$content.find('.o_matrix_input').filter((k, v) => v.attributes.ptav_ids.nodeValue === str)[0].focus();
            } else {
                MatrixDialog.$content.find('.o_matrix_input:first()').focus();
            }
        });
    },

});

return SectionAndNoteFieldOne2Many;

});
