odoo.define('barcodes.FormView', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var core = require('web.core');
var FormController = require('web.FormController');

var _t = core._t;

const reservedBarcodePrefixes = ['O-CMD'];


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
     * @returns {Promise}
     */
    _barcodeAddX2MQuantity: function (barcode, activeBarcode) {
        if (this.mode === 'readonly') {
            this.displayNotification({ message: _t('Enable edit mode to modify this document'), type: 'danger' });
            return Promise.reject();
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
    _barcodePagerFirst: async function () {
        return this._updatePage(() => 1);
    },
    /**
     * @private
     */
    _barcodePagerLast: async function () {
        return this._updatePage((min, state) => state.count);
    },
    /**
     * @private
     */
    _barcodePagerNext: function () {
        return this._updatePage((min, state) => {
            min += 1;
            if (min > state.count) {
                min = 1;
            }
            return min;
        });
    },
    /**
     * @private
     */
    _barcodePagerPrevious: function () {
        return this._updatePage((min, state) => {
            min -= 1;
            if (min < 1) {
                min = state.count;
            }
            return min;
        });
    },
    /**
     * Change the current minimum value of the pager using provided function.
     * This function will be given the current minimum and state and must return
     * the updated value.
     *
     * @private
     * @param {Function(currentMin: Number, state: Object)} updater
     */
    _updatePage: async function (updater) {
        await this.mutex.exec(() => {});
        const state = this.model.get(this.handle, { raw: true });
        const pagingInfo = this._getPagingInfo(state);
        if (!pagingInfo) {
            return this.displayNotification({ message: _t('Pager unavailable'), type: 'danger' });
        }
        const currentMinimum = updater(pagingInfo.currentMinimum, state);
        const limit = pagingInfo.limit;
        const reloadParams = state.groupedBy && state.groupedBy.length ? {
                groupsLimit: limit,
                groupsOffset: currentMinimum - 1,
            } : {
                limit,
                offset: currentMinimum - 1,
            };
        await this.reload(reloadParams);
        // reset the scroll position to the top on page changed only
        if (state.limit === limit) {
            this.trigger_up('scrollTo', { top: 0 });
        }
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
     * @returns {Promise}
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
    },
    /**
     * @private
     */
    _barcodeStopListening: function () {
        core.bus.off('barcode_scanned', this, this._barcodeScanned);
    },
    /**
     * @private
     * @param {Object} current record
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {Object} activeBarcode: options sent by the field who use barcode features
     * @returns {Promise}
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
     * @returns {Promise}
     */
    _barcodeActiveScanned: function (method, barcode, activeBarcode) {
        var self = this;
        var methodDef;
        var def = new Promise(function (resolve, reject) {
            if (typeof method === 'string') {
                methodDef = self[method](barcode, activeBarcode);
            } else {
                methodDef = method.call(self, barcode, activeBarcode);
            }
            methodDef
                .then(function () {
                    var record = self.model.get(self.handle);
                    var candidate = self._getBarCodeRecord(record, barcode, activeBarcode);
                    activeBarcode.candidate = candidate;
                })
                .then(resolve, resolve);
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
     * @returns {Promise}
     */
    _barcodeScanned: function (barcode, target) {
        var self = this;
        return this.barcodeMutex.exec(function () {
            var prefixed = _.any(reservedBarcodePrefixes,
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
                self.displayNotification({ title: _t('Undefined barcode command'), message: barcode, type: 'danger' });
            }
            return self.alive(Promise.all(defs)).then(function () {
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
});

});
