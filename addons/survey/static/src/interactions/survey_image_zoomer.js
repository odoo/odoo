import publicWidget from '@web/legacy/js/public/public_widget';

export const SurveyImageZoomer = publicWidget.Widget.extend({
    template: 'survey.survey_image_zoomer',
    events: {
        'wheel .o_survey_img_zoom_image': 'onImageScroll',
        'click': 'onZoomerClick',
        'click .o_survey_img_zoom_in_btn': 'onZoomInClick',
        'click .o_survey_img_zoom_out_btn': 'onZoomOutClick',
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
     * @param {WheelEvent} ev
     */
    onImageScroll(ev) {
        ev.preventDefault();
        ev = ev.originalEvent;
        if (ev.wheelDelta > 0 || ev.detail < 0) {
            this.addZoomSteps(1);
        } else {
            this.addZoomSteps(-1);
        }
    },

    /**
     * Allow user to close by clicking anywhere (mobile...). Destroying the modal
     * without using 'hide' would leave a modal-open in the view.
     * @param {Event} e
     */
    onZoomerClick(e) {
        e.preventDefault();
        this.$el.modal('hide');
    },
    /**
     * @private
     * @param {Event} e
     */
    onZoomInClick(e) {
        e.stopPropagation();
        this.addZoomSteps(1);
    },
    /**
     * @private
     * @param {Event} e
     */
    onZoomOutClick(e) {
        e.stopPropagation();
        this.addZoomSteps(-1);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Zoom in / out the image by changing the scale by the given number of steps.
     * @param {integer} zoomStepNumber - Number of zoom steps applied to the scale of
     * the image. It can be negative, in order to zoom out. Step is set to 0.1.
     */
    addZoomSteps(zoomStepNumber) {
        const image = this.el.querySelector(".o_survey_img_zoom_image");
        const body = this.el.querySelector(".o_survey_img_zoom_body");
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
