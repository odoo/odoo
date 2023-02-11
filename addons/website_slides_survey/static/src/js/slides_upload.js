odoo.define('website_slides_survey.upload_modal', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var sessionStorage = window.sessionStorage;
var SlidesUpload = require('@website_slides/js/slides_upload')[Symbol.for("default")];

/**
 * Management of the new 'certification' slide_type
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
        if (ev.added && ev.added.text) {
            this.$("input#name").val(ev.added.text);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overridden to add the "certification" slide type
     *
     * @override
     * @private
     */
    _setup: function () {
        this._super.apply(this, arguments);
        this.slide_type_data['certification'] = {
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
                .closest('.form-group')
                .find('.select2-container');
            $select2Container.removeClass('is-invalid is-valid');
            if ($certificationInput.is(':invalid')) {
                $select2Container.addClass('is-invalid');
            } else if ($certificationInput.is(':valid')) {
                $select2Container.addClass('is-valid');
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

    /**
     * Overridde to handle certification created on-the-fly: toaster will hold
     * survey edit url, need to put it in session to use it in CertificationUploadToast
     *
     * @override
     * @private
     */
    _onFormSubmitDone: function (data) {
        if (!data.error && data.redirect_to_certification) {
            sessionStorage.setItem("survey_certification_url", data.redirect_url);
            window.location.reload();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

SlidesUpload.websiteSlidesUpload.include({
    xmlDependencies: (SlidesUpload.websiteSlidesUpload.prototype.xmlDependencies || []).concat(
        ["/website_slides_survey/static/src/xml/website_slide_upload.xml"]
    ),
});

});
