odoo.define('website_slides_survey.upload_modal', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var SlidesUpload = require('@website_slides/js/slides_upload')[Symbol.for("default")];

/**
 * Management of the new 'certification' slide_category
 */
SlidesUpload.SlideUploadDialog.include({
    events: _.extend({}, SlidesUpload.SlideUploadDialog.prototype.events || {}, {
        'change input#certification_id': '_onChangeCertification'
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

   /**
    * Will automatically set the title of the slide to the title of the chosen certification
    */
    _onChangeCertification: function (ev) {
        const $inputElement = this.$("input#name");
        if (ev.added) {
            this.$('.o_error_no_certification').addClass('d-none');
            this.$('#certification_id').parent().find('.select2-container').removeClass('is-invalid');
            if (ev.added.text && !$inputElement.val().trim()) {
                $inputElement.val(ev.added.text);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overridden to add the "certification" slide category
     *
     * @override
     * @private
     */
    _setup: function () {
        this._super.apply(this, arguments);
        this.slide_category_data['certification'] = {
            icon: 'fa-trophy',
            label: _t('Certification'),
            template: 'website.slide.upload.modal.certification',
        };
    },
    /**
     * Overridden to add certifications management in select2
     *
     * @override
     * @private
     */
    _bindSelect2Dropdown: function () {
        this._super.apply(this, arguments);

        var self = this;
        this.$('#certification_id').select2(this._select2Wrapper(_t('Certification'), false,
            function () {
                return self._rpc({
                    route: '/slides_survey/certification/search_read',
                    params: {
                        fields: ['title'],
                    }
                });
            }, 'title')
        );
    },
    /**
     * The select2 field makes the "required" input hidden on the interface.
     * We need to make the "certification" field required so we override this method
     * to handle validation in a fully custom way.
     *
     * @override
     * @private
     */
    _formValidate: function () {
        var result = this._super.apply(this, arguments);

        var $certificationInput = this.$('#certification_id');
        if ($certificationInput.length !== 0) {
            var $select2Container = $certificationInput
                .parent()
                .find('.select2-container');
            var $errorContainer = $('.o_error_no_certification');
            $select2Container.removeClass('is-invalid is-valid');
            if ($certificationInput.is(':invalid')) {
                $select2Container.addClass('is-invalid');
                $errorContainer.removeClass('d-none');
            } else if ($certificationInput.is(':valid')) {
                $select2Container.addClass('is-valid');
                $errorContainer.addClass('d-none');
            }
        }

        return result;
    },
    /**
     * Overridden to add the 'certification' field into the submitted values
     *
     * @override
     * @private
     */
    _getSelect2DropdownValues: function () {
        var result = this._super.apply(this, arguments);

        var certificateValue = this.$('#certification_id').select2('data');
        var survey = {};
        if (certificateValue) {
            if (certificateValue.create) {
                survey.id = false;
                survey.title = certificateValue.text;
            } else {
                survey.id = certificateValue.id;
            }
        }
        result['survey'] = survey;
        return result;
    },
});

});
