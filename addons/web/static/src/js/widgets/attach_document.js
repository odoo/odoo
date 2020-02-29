odoo.define('web.AttachDocument', function (require) {
"use static";

var core = require('web.core');
var framework = require('web.framework');
var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var _t = core._t;

var AttachDocument = Widget.extend({
    template: 'AttachDocument',
    events: {
        'click': '_onClickAttachDocument',
        'change input.o_input_file': '_onFileChanged',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} record
     * @param {Object} nodeInfo
     */
    init: function (parent, record, nodeInfo) {
        this._super.apply(this, arguments);
        this.res_id = record.res_id;
        this.res_model = record.model;
        this.state = record;
        this.node = nodeInfo;
        this.fileuploadID = _.uniqueId('o_fileupload');
    },
    /**
     * @override
     */
    start: function () {
        $(window).on(this.fileuploadID, this._onFileLoaded.bind(this));
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        $(window).off(this.fileuploadID);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // private
    //--------------------------------------------------------------------------

    /**
     * Helper function to display a warning that some fields have an invalid
     * value. This is used when a save operation cannot be completed.
     *
     * @private
     * @param {string[]} invalidFields - list of field names
     */
    _notifyInvalidFields: function (invalidFields) {
        var fields = this.state.fields;
        var warnings = invalidFields.map(function (fieldName) {
            var fieldStr = fields[fieldName].string;
            return _.str.sprintf('<li>%s</li>', _.escape(fieldStr));
        });
        warnings.unshift('<ul>');
        warnings.push('</ul>');
        this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
     },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens File Explorer dialog if all fields are valid and record is saved
     *
     * @private
     * @param {Event} ev
     */
    _onClickAttachDocument: function (ev) {
        if ($(ev.target).is('input.o_input_file')) {
            return;
        }
        var fieldNames = this.getParent().canBeSaved(this.state.id);
        if (fieldNames.length) {
            return this._notifyInvalidFields(fieldNames);
        }
        // We want to save record on widget click and then open File Selection Explorer
        // but due to this security restriction give warning to save record first.
        // https://stackoverflow.com/questions/29728705/trigger-click-on-input-file-on-asynchronous-ajax-done/29873845#29873845
        if (!this.res_id) {
            return this.do_warn(_t('Warning : You have to save first before attaching a file.'));
        }
        this.$('input.o_input_file').trigger('click');
    },
    /**
     * Submits file
     *
     * @private
     * @param {Event} ev
     */
    _onFileChanged: function (ev) {
        ev.stopPropagation();
        this.$('form.o_form_binary_form').trigger('submit');
        framework.blockUI();
    },
    /**
     * Call action given as node attribute after file submission
     *
     * @private
     */
    _onFileLoaded: function () {
        var self = this;
        // the first argument isn't a file but the jQuery.Event
        var files = Array.prototype.slice.call(arguments, 1);
        return new Promise(function (resolve) {
            if (self.node.attrs.action) {
                self._rpc({
                    model: self.res_model,
                    method: self.node.attrs.action,
                    args: [self.res_id],
                    kwargs: {
                        attachment_ids: _.map(files, function (file) {
                            return file.id;
                        }),
                    }
                }).then(function () {
                    resolve();
                });
            } else {
                resolve();
            }
        }).then(function () {
            self.trigger_up('reload');
            framework.unblockUI();
        });
    },

});
widgetRegistry.add('attach_document', AttachDocument);
});
