import { SlideUploadCategory } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_category";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

patch(SlideUploadCategory.prototype, {
    setup() {
        super.setup();
        this.state.choices.certifications = [];
        this.state.choices.certificationId = "";
        this.state.showCertificationRequiredError = false;
        onWillStart(async () => {
            const results = await rpc("/slides_survey/certification/search_read", {
                fields: ["title"],
            });

            this.state.choices.certifications = results.read_results.map((certification) => {
                return { value: certification.id, label: certification.title };
            });
        });
    },

    get displayCertificationValue() {
        return this.state.choices.certificationId
            ? this.state.choices.certifications.find(
                  (c) => c.value === this.state.choices.certificationId
              ).label
            : _t("Select a certification");
    },

    _formValidate() {
        const isFormValid = super._formValidate();
        if (this.props.slideCategory === "certification" && !this.state.choices.certificationId) {
            this.state.showCertificationRequiredError = true;
            return false;
        }
        return isFormValid;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onCertificationSelect(value) {
        this.state.choices.certificationId = value;
        this.state.form.slideName = this.state.choices.certifications.find(
            (c) => c.value === value
        ).label;
        this.state.showCertificationRequiredError = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getSelectMenuValues() {
        const result = super._getSelectMenuValues();
        if (this.state.choices.certifications.length > 0) {
            if (this._toCreate(this.state.choices.certificationId)) {
                const certification = this.state.choices.certifications.find(
                    (cert) => cert.value === this.state.choices.certificationId
                );
                result.survey = {
                    id: false,
                    title: certification.label,
                };
            } else {
                result.survey = { id: parseInt(this.state.choices.certificationId, 10) };
            }
        }

        return result;
    },
});
