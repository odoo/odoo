odoo.define('web.Signature', function (require) {
    "use strict";

    var AbstractFieldBinary = require('web.basic_fields').AbstractFieldBinary;
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var field_utils = require('web.field_utils');
    var NameAndSignature = require('web.name_and_signature').NameAndSignature;
    var registry = require('web.field_registry');
    var session = require('web.session');
    var utils = require('web.utils');


    var qweb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

// The goal of this dialog is to ask the user a signature request.
// It uses @see SignNameAndSignature for the name and signature fields.
var SignatureDialog = Dialog.extend({
    template: 'web.signature_dialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web/static/src/xml/name_and_signature.xml']
    ),
    custom_events: {
        'signature_changed': '_onChangeSignature',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} options
     * @param {string} [options.title='Adopt Your Signature'] - modal title
     * @param {string} [options.size='medium'] - modal size
     * @param {Object} [options.nameAndSignatureOptions={}] - options for
     *  @see NameAndSignature.init()
     */
    init: function (parent, options) {
        var self = this;
        options = options || {};

        options.title = options.title || _t("Adopt Your Signature");
        options.size = options.size || 'medium';
        options.technical = false;

        if (!options.buttons) {
            options.buttons = [];
            options.buttons.push({text: _t("Adopt and Sign"), classes: "btn-primary", disabled: true, click: function (e) {
                self._onConfirm();
            }});
            options.buttons.push({text: _t("Cancel"), close: true});
        }

        this._super(parent, options);

        this.nameAndSignature = new NameAndSignature(this, options.nameAndSignatureOptions);
    },
    /**
     * Start the nameAndSignature widget and wait for it.
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this.nameAndSignature.appendTo($('<div>')),
            this._super.apply(this, arguments)
        ]);
    },
    /**
     * Initialize the name and signature widget when the modal is opened.
     *
     * @override
     */
    start: function () {
        var self = this;
        this.$primaryButton = this.$footer.find('.btn-primary');

        this.opened().then(function () {
            self.$('.o_web_sign_name_and_signature').replaceWith(self.nameAndSignature.$el);
            // initialize the signature area
            self.nameAndSignature.resetSignature();
        });

        return this._super.apply(this, arguments);
    },

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * Returns whether the drawing area is currently empty.
     *
     * @see NameAndSignature.isSignatureEmpty()
     * @returns {boolean} Whether the drawing area is currently empty.
     */
    isSignatureEmpty: function () {
        return this.nameAndSignature.isSignatureEmpty();
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Toggles the submit button depending on the signature state.
     *
     * @private
     */
    _onChangeSignature: function () {
        var isEmpty = this.nameAndSignature.isSignatureEmpty();
        this.$primaryButton.prop('disabled', isEmpty);
    },
    /**
     * Upload the signature image when confirm.
     *
     * @private
     */
    _onConfirm: function (fct) {
        this.trigger_up('upload_signature', {
            name: this.nameAndSignature.getName(),
            signatureImage: this.nameAndSignature.getSignatureImage(),
        });
    },
});

var FieldBinarySignature = AbstractFieldBinary.extend({
    description: _lt("Signature"),
    fieldDependencies: _.extend({}, AbstractFieldBinary.prototype.fieldDependencies, {
        __last_update: {type: 'datetime'},
    }),
    resetOnAnyFieldChange: true,
    custom_events: _.extend({}, AbstractFieldBinary.prototype.custom_events, {
        upload_signature: '_onUploadSignature',
    }),
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
        'click .o_signature': '_onClickSignature',
    }),
    template: null,
    supportedFieldTypes: ['binary'],
    file_type_magic_word: {
        '/': 'jpg',
        'R': 'gif',
        'i': 'png',
        'P': 'svg+xml',
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This widget must always have render even if there are no signature.
     * In edit mode, the real value is return to manage required fields.
     *
     * @override
     */
    isSet: function () {
        if (this.mode === 'edit') {
            return this.value;
        }
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders an empty signature or the saved signature. Both must have the same size.
     *
     * @override
     * @private
     */

    _render: function () {
        var self = this;
        var displaySignatureRatio = 3;
        var url;
        var $img;
        var width = this.nodeOptions.size ? this.nodeOptions.size[0] : this.attrs.width;
        var height = this.nodeOptions.size ? this.nodeOptions.size[1] : this.attrs.height;
        if (this.value) {
            if (!utils.is_bin_size(this.value)) {
                // Use magic-word technique for detecting image type
                url = 'data:image/' + (this.file_type_magic_word[this.value[0]] || 'png') + ';base64,' + this.value;
            } else {
                url = session.url('/web/image', {
                    model: this.model,
                    id: JSON.stringify(this.res_id),
                    field: this.nodeOptions.preview_image || this.name,
                    // unique forces a reload of the image when the record has been updated
                    unique: field_utils.format.datetime(this.recordData.__last_update).replace(/[^0-9]/g, ''),
                });
            }
            $img = $(qweb.render("FieldBinarySignature-img", {widget: this, url: url}));
        } else {
            $img = $('<div class="o_signature o_signature_empty"><svg></svg><p>' + _t('SIGNATURE') + '</p></div>');
            if (width && height) {
                width = Math.min(width, displaySignatureRatio * height);
                height = width / displaySignatureRatio;
            } else if (width) {
                height = width / displaySignatureRatio;
            } else if (height) {
                width = height * displaySignatureRatio;
            }
        }
        if (width) {
            $img.attr('width', width);
            $img.css('max-width', width + 'px');
        }
        if (height) {
            $img.attr('height', height);
            $img.css('max-height', height + 'px');
        }
        this.$('> div').remove();
        this.$('> img').remove();

        this.$el.prepend($img);

        $img.on('error', function () {
            self._clearFile();
            $img.attr('src', self.placeholder);
            self.do_warn(_t("Image"), _t("Could not display the selected image."));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If the view is in edit mode, open dialog to sign.
     *
     * @private
     */
    _onClickSignature: function () {
        var self = this;
        if (this.mode === 'edit') {

            var nameAndSignatureOptions = {
                mode: 'draw',
                displaySignatureRatio: 3,
                signatureType: 'signature',
                noInputName: true,
            };

            if (this.nodeOptions.full_name) {
                var signName;
                if (this.fields[this.nodeOptions.full_name].type === 'many2one') {
                    // If m2o is empty, it will have falsy value in recordData
                    signName = this.recordData[this.nodeOptions.full_name] && this.recordData[this.nodeOptions.full_name].data.display_name;
                } else {
                     signName = this.recordData[this.nodeOptions.full_name];
                 }
                nameAndSignatureOptions.defaultName = (signName === '') ? undefined : signName;
            }

            nameAndSignatureOptions.defaultFont = this.nodeOptions.default_font || '';
            this.signDialog = new SignatureDialog(self, {nameAndSignatureOptions: nameAndSignatureOptions});

            this.signDialog.open();
        }
    },

    /**
     * Upload the signature image if valid and close the dialog.
     *
     * @private
     */
    _onUploadSignature: function (ev) {
        var signatureImage = ev.data.signatureImage;
        if (signatureImage !== this.signDialog.emptySignature) {
            var data = signatureImage[1];
            var type = signatureImage[0].split('/')[1];
            this.on_file_uploaded(data.length, ev.data.name, type, data);
        }
        this.signDialog.close();
    }
});

registry.add('signature', FieldBinarySignature);

});
