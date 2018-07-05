odoo.define('barcodes.FormView', function (require) {
"use strict";

var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');

var _t = core._t;


FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        activeBarcode: '_barcodeActivated',
    }),

    /**
     * add default barcode commands for from view
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.activeBarcode = {
            form_view: {
                commands: {
                    'O-CMD.EDIT': this._barcodeEdit.bind(this),
                    'O-CMD.DISCARD': this._barcodeDiscard.bind(this),
                    'O-CMD.SAVE': this._barcodeSave.bind(this),
                    'O-CMD.PREV': this._barcodePagerPrevious.bind(this),
                    'O-CMD.NEXT': this._barcodePagerNext.bind(this),
                    'O-CMD.PAGER-FIRST': this._barcodePagerFirst.bind(this),
                    'O-CMD.PAGER-LAST': this._barcodePagerLast.bind(this),
                },
            },
        };

        this.barcodeMutex = new concurrency.Mutex();
        this._barcodeStartListening();
    },
    /**
     * @override
     */
    destroy: function () {
        this._barcodeStopListening();
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {Deferred}
     */
    _barcodeAddX2MQuantity: function (barcode, activeBarcode) {
        if (this.mode === 'readonly') {
            this.do_warn(_t('Error: Document not editable'),
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
     */
    _barcodeDiscard: function () {
        return this.discardChanges();
    },
    /**
     * @private
     */
    _barcodeEdit: function () {
        return this._setMode('edit');
    },
    /**
     * @private
     */
    _barcodePagerFirst: function () {
        var self = this;
        return this.mutex.exec(function () {}).then(function () {
            if (!self.pager) {
                self.do_warn(_t('Error: Pager not available'));
                return;
            }
            self.pager.updateState({
                current_min: 1,
            }, {notifyChange: true});
        });
    },
    /**
     * @private
     */
    _barcodePagerLast: function () {
        var self = this;
        return this.mutex.exec(function () {}).then(function () {
            if (!self.pager) {
                self.do_warn(_t('Error: Pager not available'));
                return;
            }
            var state = self.model.get(self.handle, {raw: true});
            self.pager.updateState({
                current_min: state.count,
            }, {notifyChange: true});
        });
    },
    /**
     * @private
     */
    _barcodePagerNext: function () {
        var self = this;
        return this.mutex.exec(function () {}).then(function () {
            if (!self.pager) {
                self.do_warn(_t('Error: Pager not available'));
                return;
            }
            self.pager.next();
        });
    },
    /**
     * @private
     */
    _barcodePagerPrevious: function () {
        var self = this;
        return this.mutex.exec(function () {}).then(function () {
            if (!self.pager) {
                self.do_warn(_t('Error: Pager not available'));
                return;
            }
            self.pager.previous();
        });
    },
    /**
     * Returns true iff the given barcode matches the given record (candidate).
     *
     * @private
     * @param {Object} candidate: record in the x2m
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {boolean}
     */
    _barcodeRecordFilter: function (candidate, barcode, activeBarcode) {
        return candidate.data.product_barcode === barcode;
    },
    /**
     * @private
     */
    _barcodeSave: function () {
        return this.saveRecord();
    },
    /**
     * @private
     * @param {Object} candidate: record in the x2m
     * @param {Object} current record
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {Deferred}
     */
    _barcodeSelectedCandidate: function (candidate, record, barcode, activeBarcode, quantity) {
        var changes = {};
        var candidateChanges = {};
        candidateChanges[activeBarcode.quantity] = quantity ? quantity : candidate.data[activeBarcode.quantity] + 1;
        changes[activeBarcode.fieldName] = {
            operation: 'UPDATE',
            id: candidate.id,
            data: candidateChanges,
        };
        return this.model.notifyChanges(this.handle, changes, {notifyChange: activeBarcode.notifyChange});
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
     * @param {Object} current record
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {Deferred}
     */
    _barcodeWithoutCandidate: function (record, barcode, activeBarcode) {
        var changes = {};
        changes[activeBarcode.name] = barcode;
        return this.model.notifyChanges(record.id, changes);
    },
    /**
     * @private
     * @param {Object} current record
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {Object|undefined}
     */
    _getBarCodeRecord: function (record, barcode, activeBarcode) {
        var self = this;
        if (!activeBarcode.fieldName || !record.data[activeBarcode.fieldName]) {
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
     * @param {string} event.data.name: the current field name
     * @param {string} [event.data.fieldName] optional for x2many sub field
     * @param {boolean} [event.data.notifyChange] optional for x2many sub field
     *     do not trigger on change server side if a candidate has been found
     * @param {string} [event.data.quantity] optional field to increase quantity
     * @param {Object} [event.data.commands] optional added methods
     *     can use comand with specific barcode (with ReservedBarcodePrefixes)
     *     or change 'barcode' for all other received barcodes
     *     (e.g.: 'O-CMD.MAIN-MENU': function ..., barcode: function () {...})
     */
    _barcodeActivated: function (event) {
        event.stopPropagation();
        var name = event.data.name;
        this.activeBarcode[name] = {
            name: name,
            handle: this.handle,
            target: event.target,
            widget: event.target.attrs && event.target.attrs.widget,
            setQuantityWithKeypress: !! event.data.setQuantityWithKeypress,
            fieldName: event.data.fieldName,
            notifyChange: (event.data.notifyChange !== undefined) ? event.data.notifyChange : true,
            quantity: event.data.quantity,
            commands: event.data.commands || {},
            candidate: this.activeBarcode[name] && this.activeBarcode[name].handle === this.handle ?
                this.activeBarcode[name].candidate : null,
        };

        // we want to disable autofocus when activating the barcode to avoid
        // putting the scanned value in the focused field
        this.disableAutofocus = true;
    },
    /**
     * @private
     * @param {string|function} method defined by the commands options
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
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
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {DOM Object} target
     * @returns {Deferred}
     */
    _barcodeScanned: function (barcode, target) {
        var self = this;
        return this.barcodeMutex.exec(function () {
            var prefixed = _.any(BarcodeEvents.ReservedBarcodePrefixes,
                    function (reserved) {return barcode.indexOf(reserved) === 0;});
            var hasCommand = false;
            var defs = [];
            if (! $.contains(target, self.el)) {
                return;
            }
            for (var k in self.activeBarcode) {
                var activeBarcode = self.activeBarcode[k];
                // Handle the case where there are several barcode widgets on the same page. Since the
                // event is global on the page, all barcode widgets will be triggered. However, we only
                // want to keep the event on the target widget.
                var methods = self.activeBarcode[k].commands;
                var method = prefixed ? methods[barcode] : methods.barcode;
                if (method) {
                    if (prefixed) {
                        hasCommand = true;
                    }
                    defs.push(self._barcodeActiveScanned(method, barcode, activeBarcode));
                }
            }
            if (prefixed && !hasCommand) {
                self.do_warn(_t('Error: Barcode command is undefined'), barcode);
            }
            return self.alive($.when.apply($, defs)).then(function () {
                if (!prefixed) {
                    // remember the barcode scanned for the quantity listener
                    self.current_barcode = barcode;
                    // redraw the view if we scanned a real barcode (required if
                    // we manually apply the change in JS, e.g. incrementing the
                    // quantity)
                    self.update({}, {reload: false});
                }
            });
        });
    },
    /**
     * @private
     * @param {KeyEvent} event
     */
    _quantityListener: function (event) {
        var character = String.fromCharCode(event.which);

        if (! $.contains(event.target, this.el)) {
            return;
        }
        // only catch the event if we're not focused in
        // another field and it's a number
        if (!$(event.target).is('body, .modal') || !/[0-9]/.test(character)) {
            return;
        }

        var barcodeInfos = _.filter(this.activeBarcode, 'setQuantityWithKeypress');
        if (!barcodeInfos.length) {
            return;
        }

        if (!_.compact(_.pluck(barcodeInfos, 'candidate')).length) {
            return this.do_warn(_t('Error: No last scanned barcode'),
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
     * @param {string} character
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     */
    _quantityOpenDialog: function (character, activeBarcode) {
        var self = this;
        var $content = $('<div>').append($('<input>', {type: 'text', class: 'o_set_qty_input'}));
        this.dialog = new Dialog(this, {
            title: _t('Set quantity'),
            buttons: [{text: _t('Select'), classes: 'btn-primary', close: true, click: function () {
                var new_qty = this.$content.find('.o_set_qty_input').val();
                var record = self.model.get(self.handle);
                return self._barcodeSelectedCandidate(activeBarcode.candidate, record,
                        self.current_barcode, activeBarcode, parseFloat(new_qty))
                .then(function () {
                    self.update({}, {reload: false});
                });
            }}, {text: _t('Discard'), close: true}],
            $content: $content,
        });
        this.dialog.opened().then(function () {
            // This line set the value of the key which triggered the _set_quantity in the input
            var $input = self.dialog.$('.o_set_qty_input').focus().val(character);
            var $selectBtn = self.dialog.$footer.find('.btn-primary');
            $input.on('keypress', function (event){
                if (event.which === 13) {
                    event.preventDefault();
                    $input.off();
                    $selectBtn.click();
                }
            });
        });
        this.dialog.open();
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
            if (!$button.hasClass('o_invisible_modifier')) {
                $button.click();
            }
            return $.when();
        };
        var name = node.attrs.name;
        if (node.attrs.string) {
            name = name + '_' + node.attrs.string;
        }

        this.trigger_up('activeBarcode', {
            name: name,
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
    /**
     * Add barcode event handler
     *
     * @override
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagButton: function (node) {
        var $button = this._super.apply(this, arguments);
        if (node.attrs.barcode_trigger) {
            this._barcodeButtonHandler($button, node);
        }
        return $button;
    }
});

BarcodeEvents.ReservedBarcodePrefixes.push('O-BTN');

});
