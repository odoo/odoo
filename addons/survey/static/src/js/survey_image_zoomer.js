/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';

export const SurveyImageZoomer = publicWidget.Widget.extend({
    template: 'survey.survey_image_zoomer',
    events: {
        'wheel .o_survey_img_zoom_image': '_onImgScroll',
        'click': '_onZoomerClick',
        'click .o_survey_img_zoom_in_btn': '_onZoomInClick',
        'click .o_survey_img_zoom_out_btn': '_onZoomOutClick',
    },
    /**
     * @override
     */
    init(params) {
        this.zoomImageScale = 1;
        // The image is needed to render the template survey_image_zoom.
        this.sourceImage = params.sourceImage;
        this._super(... arguments);
    },
    /**
     * Open a transparent modal displaying the survey choice image.
     * @override
     */
    async start() {
        const superResult = await this._super(...arguments);
        // Prevent having hidden modal in the view.
        this.$el.on('hidden.bs.modal', () => this.destroy());
        this.$el.modal('show');
        return superResult;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Zoom in/out image on scrolling
     *
     * @private
     * @param {WheelEvent} e
     */
    _onImgScroll(e) {
        e.preventDefault();
        if (e.originalEvent.wheelDelta > 0 || e.originalEvent.detail < 0) {
            this._addZoomSteps(1);
        } else {
            this._addZoomSteps(-1);
        }
    },
    /**
     * Allow user to close by clicking anywhere (mobile...). Destroying the modal
     * without using 'hide' would leave a modal-open in the view.
     * @private
     * @param {Event} e
     */
     _onZoomerClick(e) {
        e.preventDefault();
        this.$el.modal('hide');
    },
    /**
     * @private
     * @param {Event} e
     */
    _onZoomInClick(e) {
        e.stopPropagation();
        this._addZoomSteps(1);
    },
    /**
     * @private
     * @param {Event} e
     */
    _onZoomOutClick(e) {
        e.stopPropagation();
        this._addZoomSteps(-1);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Zoom in / out the image by changing the scale by the given number of steps.
     *
     * @private
     * @param {integer} zoomStepNumber - Number of zoom steps applied to the scale of
     * the image. It can be negative, in order to zoom out. Step is set to 0.1.
     */
     _addZoomSteps(zoomStepNumber) {
        const image = this.el.querySelector('.o_survey_img_zoom_image');
        const body = this.el.querySelector('.o_survey_img_zoom_body');
        const imageWidth = image.clientWidth;
        const imageHeight = image.clientHeight;
        const bodyWidth = body.clientWidth;
        const bodyHeight = body.clientHeight;
        const newZoomImageScale = this.zoomImageScale + zoomStepNumber * 0.1;
        if (newZoomImageScale <= 0.2) {
            // Prevent the user from de-zooming too much
            return;
        }
        if (zoomStepNumber > 0 && (imageWidth * newZoomImageScale > bodyWidth || imageHeight * newZoomImageScale > bodyHeight)) {
            // Prevent to user to further zoom in as the new image would becomes too large or too high for the screen.
            // Dezooming is still allowed to bring back image into frame (use case: resizing screen).
            return;
        }
        // !important is needed to prevent default 'no-transform' on smaller screens.
        image.setAttribute('style', 'transform: scale(' + newZoomImageScale + ') !important');
        this.zoomImageScale = newZoomImageScale;
    },
});
