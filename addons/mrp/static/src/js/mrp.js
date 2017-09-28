odoo.define('mrp.mrp_state', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basic_fields = require('web.basic_fields');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');
var utils = require('web.utils');

var FieldBinaryFile = basic_fields.FieldBinaryFile;
var _t = core._t;

var FieldPdfViewer = FieldBinaryFile.extend({
    supportedFieldTypes: ['binary'],
    template: 'FieldPdfViewer',
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.PDFViewerApplication = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {DOMElement} iframe
     */
    _disableButtons: function (iframe) {
        if (this.mode === 'readonly') {
            $(iframe).contents().find('button#download').hide();
        }
        $(iframe).contents().find('button#openFile').hide();
    },
    /**
     * @private
     * @returns {string} the pdf viewer URI
     */
    _getURI: function () {
        var queryObj = {
            model: this.model,
            field: this.name,
            id: this.res_id,
        };
        var page = this.recordData[this.name + '_page'] || 1;
        var queryString = $.param(queryObj);
        var url = encodeURIComponent('/web/image?' + queryString);
        var viewerURL = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewerURL + url + '#page=' + page;
    },
    /**
     * @private
     * @override
     */
    _render: function () {
        var self = this;
        var $pdfViewer = this.$('.o_form_pdf_controls').children().add(this.$('.o_pdfview_iframe'));
        var $selectUpload = this.$('.o_select_file_button').first();
        var $iFrame = this.$('.o_pdfview_iframe');

        $iFrame.on('load', function () {
            self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
            self._disableButtons(this);
        });
        if (this.mode === "readonly" && this.value) {
            $iFrame.attr('src', this._getURI());
        } else {
            if (this.value) {
                var binSize = utils.is_bin_size(this.value);
                $pdfViewer.removeClass('o_hidden');
                $selectUpload.addClass('o_hidden');
                if (binSize) {
                    $iFrame.attr('src', this._getURI());
                }
            } else {
                $pdfViewer.addClass('o_hidden');
                $selectUpload.removeClass('o_hidden');
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Event} ev
     */
    on_file_change: function (ev) {
        this._super.apply(this, arguments);
        if (this.PDFViewerApplication) {
            var files = ev.target.files;
            if (!files || files.length === 0) {
              return;
            }
            var file = files[0];
            // TOCheck: is there requirement to fallback on FileReader if browser don't support URL
            this.PDFViewerApplication.open(URL.createObjectURL(file), 0);
        }
    },
    /**
     * Remove the behaviour of on_save_as in FieldBinaryFile.
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    on_save_as: function (ev) {
        ev.stopPropagation();
    },

});

/**
 * This widget is used to display the availability on a workorder.
 */
var SetBulletStatus = AbstractField.extend({
    // as this widget is based on hardcoded values, use it in another context
    // probably won't work
    // supportedFieldTypes: ['selection'],
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.classes = this.nodeOptions && this.nodeOptions.classes || {};
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);
        var bullet_class = this.classes[this.value] || 'default';
        if (this.value) {
            var title = this.value === 'waiting' ? _t('Waiting Materials') : _t('Ready to produce');
            this.$el.attr({'title': title, 'style': 'display:inline'});
            this.$el.removeClass('text-success text-danger text-default');
            this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
        }
    }
});

var TimeCounter = AbstractField.extend({
    supportedFieldTypes: [],
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: 'mrp.workcenter.productivity',
            method: 'search_read',
            domain: [
                ['workorder_id', '=', this.record.data.id],
                ['user_id', '=', this.getSession().uid],
            ],
        }).then(function (result) {
            if (self.mode === 'readonly') {
                var currentDate = new Date();
                self.duration = 0;
                _.each(result, function (data) {
                    self.duration += data.date_end ?
                        self._getDateDifference(data.date_start, data.date_end) :
                        self._getDateDifference(time.auto_str_to_date(data.date_start), currentDate);
                });
            }
        });
        return $.when(this._super.apply(this, arguments), def);
    },

    destroy: function () {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute the difference between two dates.
     *
     * @private
     * @param {string} dateStart
     * @param {string} dateEnd
     * @returns {integer} the difference in millisecond
     */
    _getDateDifference: function (dateStart, dateEnd) {
        return moment(dateEnd).diff(moment(dateStart));
    },
    /**
     * @override
     */
    _render: function () {
        this._startTimeCounter();
    },
    /**
     * @private
     */
    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (this.record.data.is_user_working) {
            this.timer = setTimeout(function () {
                self.duration += 1000;
                self._startTimeCounter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
        this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
    },
});

field_registry
    .add('bullet_state', SetBulletStatus)
    .add('mrp_time_counter', TimeCounter)
    .add('pdf_viewer', FieldPdfViewer);

});
