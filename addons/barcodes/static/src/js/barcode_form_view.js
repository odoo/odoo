odoo.define('barcodes.FormView', function (require) {
"use strict";

var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
var core = require('web.core');
var Dialog = require('web.Dialog');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');

var _t = core._t;


FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        activeBarcode: '_barcodeActivated',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.activeBarcode = {
            form_view: {
                commands: {
                    'O-CMD.NEW': 'createRecord',
                    'O-CMD.EDIT': 'toEditMode',
                    'O-CMD.CANCEL': 'discardChange',
                    'O-CMD.SAVE': function () { return this.saveRecord({reload: true}); },
                    // 'O-CMD.PAGER-PREV':
                    // 'O-CMD.PAGER-NEXT':
                }
            }
        };
        this._barcodeStartListening();
    },
    destroy: function () {
        this._barcodeStopListening();
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {any}
     */
    _barcodeAddX2MQuantity: function (barcode, activeBarcode) {
        if (this.mode === 'readonly') {
            this.do_warn(_t('Error : Document not editable'),
                _t('To modify this document, please first start edition.'));
            return new $.Deferred().reject();
        }

        var record = this.model.get(this.handle);
        var candidate = this._getBarCodeRecord(record, barcode, activeBarcode);
        if (candidate) {
            return this._barcodeSelectedCandidate(candidate, record, barcode, activeBarcode);
        } else {
            return this._barcodeWithoutCandidate(record, barcode, activeBarcode);
        }
    },
    /**
     * @private
     * @param {any} record
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {boolean}
     */
    _barcodeRecordFilter: function (record, barcode, activeBarcode) {
        return record.data.product_barcode === barcode;
    },
    /**
     * @private
     * @param {any} candidate
     * @param {any} record
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {Deferred}
     */
    _barcodeSelectedCandidate: function (candidate, record, barcode, activeBarcode) {
        var changes = {};
        changes[activeBarcode.quantity] = candidate.data[activeBarcode.quantity] + 1;
        return this.model.notifyChanges(candidate.id, changes);
    },
    /**
     * @private
     */
    _barcodeStartListening: function () {
        core.bus.on('barcode_scanned', this, this._barcodeScanned);
        core.bus.on('keypress', this, this._quantityListener);
    },

    /**
     * @private
     */
    _barcodeStopListening: function () {
        core.bus.off('barcode_scanned', this, this._barcodeScanned);
        core.bus.off('keypress', this, this._quantityListener);
    },
    /**
     * @private
     * @param {any} record
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {Deferred}
     */
    _barcodeWithoutCandidate: function (record, barcode, activeBarcode) {
        var changes = {};
        changes[activeBarcode.name] = barcode;
        return this.model.notifyChanges(record.id, changes);
    },
    /**
     * @private
     * @param {any} record
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {any}
     */
    _getBarCodeRecord: function (record, barcode, activeBarcode) {
        var self = this;
        if (!activeBarcode.fieldName) {
            return;
        }
        return _.find(record.data[activeBarcode.fieldName].data, function (record) {
            return self._barcodeRecordFilter(record, barcode, activeBarcode);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * The barcode is activate when at least one widget trigger_up 'activeBarcode' event
     * with the widget option
     *
     * @param {OdooEvent} event
     */
    _barcodeActivated: function (event) {
        event.stopPropagation();
        var name = event.data.name;
        this.activeBarcode[name] = {
            name: name,
            handle: this.handle,
            target: event.target,
            widget: event.target.attrs && event.target.attrs.widget,
            fieldName: event.data.fieldName,
            quantity: event.data.quantity,
            commands: event.data.commands || {},
            candidate: this.activeBarcode[name] && this.activeBarcode[name].handle === this.handle ?
                this.activeBarcode[name].candidate : null,
        };
    },
    /**
     * @private
     * @param {any} method
     * @param {any} barcode
     * @param {any} activeBarcode
     * @returns {Deferred}
     */
    _barcodeActiveScanned: function (method, barcode, activeBarcode) {
        var self = this;
        var methodDef;
        var def = new $.Deferred();
        if (typeof method === 'string') {
            methodDef = this[method](barcode, activeBarcode);
        } else {
            methodDef = method.call(this, barcode, activeBarcode);
        }
        methodDef
            .done(function () {
                var record = self.model.get(self.handle);
                var candidate = self._getBarCodeRecord(record, barcode, activeBarcode);
                activeBarcode.candidate = candidate;
            })
            .always(function () {
                def.resolve();
            });
        return def;
    },
    /**
     * Method called when a user scan a barcode, call each method in function of the
     * widget options then update the renderer
     *
     * @private
     * @param {string} barcode
     * @returns {Deferred}
     */
    _barcodeScanned: function (barcode, target) {
        var prefixed = _.any(BarcodeEvents.ReservedBarcodePrefixes,
                function (reserved) {return barcode.indexOf(reserved) === 0;});
        var hasCommand = false;
        var self = this;
        var defs = [];
        for (var k in this.activeBarcode) {
            var activeBarcode = this.activeBarcode[k];
            // Handle the case where there are several barcode widgets on the same page. Since the
            // event is global on the page, all barcode widgets will be triggered. However, we only
            // want to keep the event on the target widget.
            if (self.target && !$.contains(target, self.target.el)) {
                continue;
            }

            var methods = this.activeBarcode[k].commands;
            var method = prefixed ? methods[barcode] : methods.barcode;
            if (method) {
                if (prefixed) {
                    hasCommand = true;
                }
                defs.push(this._barcodeActiveScanned(method, barcode, activeBarcode));
            }
        }
        if (prefixed && !hasCommand) {
            return this.do_warn(_t('Error : Barcode command is undefined'), barcode);
        }
        return $.when.apply($, defs).then(function () {
            self.update({}, {reload: false});
        });
    },
    /**
     * @private
     * @param {any} event
     */
    _quantityListener: function (event) {
        var character = String.fromCharCode(event.which);

        // only catch the event if we're not focused in
        // another field and it's a number
        if (!$(event.target).is('body') || !/[0-9]/.test(character)) {
            return;
        }

        var barcodeInfos = _.filter(this.activeBarcode, 'setQuantityWithKeypress');
        if (!barcodeInfos.length) {
            return;
        }

        if (!_.compact(_.pluck(barcodeInfos, 'candidate')).length) {
            return this.do_warn(_t('Error : No last scanned barcode'),
                _t('To set the quantity please scan a barcode first.'));
        }

        for (var k in this.activeBarcode) {
            if (this.activeBarcode[k].candidate) {
                this._quantityOpenDialog(character, this.activeBarcode[k]);
            }
        }
    },
    /**
     * @private
     * @param {any} character
     * @param {any} activeBarcode
     */
    _quantityOpenDialog: function (character, activeBarcode) {
        var self = this;
        var $content = $('<div>').append($('<input>', {type: 'text', class: 'o_set_qty_input'}));
        this.dialog = new Dialog(this, {
            title: _t('Set quantity'),
            buttons: [{text: _t('Select'), classes: 'btn-primary', close: true, click: function () {
                var new_qty = this.$content.find('.o_set_qty_input').val();
                var values = {};
                values[activeBarcode.quantity] = parseFloat(new_qty);
                return self.model.notifyChanges(activeBarcode.candidate.id, values).then(function () {
                    self.update({}, {reload: false});
                });
            }}, {text: _t('Discard'), close: true}],
            $content: $content,
        }).open();
        // This line set the value of the key which triggered the _set_quantity in the input
        var $input = this.dialog.$content.find('.o_set_qty_input').focus().val(character);

        var $selectBtn = this.dialog.$footer.find('.btn-primary');
        $input.on('keypress', function (event){
            if (event.which === 13) {
                event.preventDefault();
                $input.off();
                $selectBtn.click();
            }
        });
    },
});


FormRenderer.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * trigger_up 'activeBarcode' to Add barcode event handler
     *
     * @private
     * @param {jQueryElement} $button
     * @param {Object} node
     */
    _barcodeButtonHandler: function ($button, node) {
        var commands = {};
        commands.barcode = function () {return $.when();};
        commands['O-BTN.' + node.attrs.barcode_trigger] = function () {
            if (!$button.hasClass('o_form_invisible')) {
                $button.click();
            }
            return $.when();
        };
        this.trigger_up('activeBarcode', {
            name: node.attrs.name,
            commands: commands
        });
    },
    /**
     * Add barcode event handler
     *
     * @override
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButton: function (node) {
        var $button = this._super.apply(this, arguments);
        if (node.attrs.barcode_trigger) {
            this._barcodeButtonHandler($button, node);
        }
        return $button;
    },
    /**
     * Add barcode event handler
     *
     * @override
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderStatButton: function (node) {
        var $button = this._super.apply(this, arguments);
        if (node.attrs.barcode_trigger) {
            this._barcodeButtonHandler($button, node);
        }
        return $button;
    },
});

BarcodeEvents.ReservedBarcodePrefixes.push('O-BTN');

});
