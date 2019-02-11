odoo.define('website_slides_survey.upload_modal', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var SlidesUpload = require('website_slides.upload_modal');

/**
 * Management of the new 'certification' slide_type
 */
SlidesUpload.SlideUploadDialog.include({
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
        if ($certificationInput.length !== 0){
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
    _getSelect2DropdownValues: function (){
        var result = this._super.apply(this, arguments);

        var certificateValue = this.$('#certification_id').select2('data');
        if (certificateValue) {
            result['survey_id'] =  certificateValue.id;
        }
        return result;
    }
});

SlidesUpload.websiteSlidesUpload.include({
    xmlDependencies: (SlidesUpload.websiteSlidesUpload.prototype.xmlDependencies || []).concat(
        ["/website_slides_survey/static/src/xml/website_slide_upload.xml"]
    ),
});

});
