import { _t } from "@web/core/l10n/translation";
import { SlideUploadDialog } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_dialog";
import { patch } from "@web/core/utils/patch";

patch(SlideUploadDialog.prototype, {
    /**
     * Overridden to add the "certification" slide category
     */
    setup() {
        super.setup();
        this.pagesTemplates["certification"] =
            "website_slides_survey.SlideCategoryTutorial.Certification";
        this.slideCategoryData["certification"] = {
            icon: "fa-trophy",
            label: _t("Certification"),
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Overridden to add certifications management
     * @param {String} slideCategory
     */
    onClickSlideCategoryIcon(slideCategory) {
        super.onClickSlideCategoryIcon(slideCategory);
        if (slideCategory === "certification") {
            this.state.title = _t("Add Certification");
        }
    },
});
