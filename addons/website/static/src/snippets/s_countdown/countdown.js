import publicWidget from "@web/legacy/js/public/public_widget";
import weUtils from "@web_editor/js/common/utils";
import { isCSSColor } from '@web/core/utils/colors';
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

const CountdownWidget = publicWidget.Widget.extend({
    selector: '.s_countdown',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        // Remove SVG previews (used to simulated canvas)
        this.$el[0].querySelectorAll('svg').forEach(el => {
            el.parentNode.remove();
        });

        this.$wrapper = this.$('.s_countdown_canvas_wrapper');
        this.$wrapper.addClass('d-flex justify-content-center');
        this.hereBeforeTimerEnds = false;
        this.endAction = this.el.dataset.endAction;
        this.endTime = parseInt(this.el.dataset.endTime);
        this.size = parseInt(this.el.dataset.size);
        this.display = this.el.dataset.display;
        if (!this.display && this.el.dataset.bsDisplay) {
            // With the BS5 upgrade script of 16.0, countdowns' data-display may
            // have been converted to data-bs-display by mistake. This will fix
            // the DOM for good measures, maybe even allowing to remove this
            // code in a few years as hopefully all current countdowns will have
            // been removed or edited (or when a proper upgrade script in a
            // future version of Odoo will be made, if necessary). TODO.
            this.display = this.el.dataset.bsDisplay;
            delete this.el.dataset.bsDisplay;
            this.el.dataset.display = this.display;
        }

        this.layout = this.el.dataset.layout;
        this.layoutBackground = this.el.dataset.layoutBackground;
        this.progressBarStyle = this.el.dataset.progressBarStyle;
        this.progressBarWeight = this.el.dataset.progressBarWeight;

        this.textColor = this._ensureCssColor(this.el.dataset.textColor);
        this.layoutBackgroundColor = this._ensureCssColor(this.el.dataset.layoutBackgroundColor);
        this.progressBarColor = this._ensureCssColor(this.el.dataset.progressBarColor);

        this.onlyOneUnit = this.display === 'd';
        this.width = parseInt(this.size);
        if (this.layout === 'boxes') {
            this.width /= 1.75;
        }
        this._initTimeDiff();

        this._render();

        this.setInterval = setInterval(this._render.bind(this), 1000);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$('.s_countdown_end_redirect_message').remove();
        this.$('.s_countdown_end_message').addClass('d-none');
        this.$('.s_countdown_text_wrapper').remove();
        this.$('.s_countdown_canvas_wrapper').removeClass('d-none');
        this.$('.s_countdown_canvas_flex').remove();

        clearInterval(this.setInterval);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Ensures the color is an actual css color. In case of a color variable,
     * the color will be mapped to hexa.
     *
     * @private
     * @param {string} color
     * @returns {string}
     */
    _ensureCssColor: function (color) {
        if (isCSSColor(color)) {
            return color;
        }
        return weUtils.getCSSVariableValue(color) || this.defaultColor;
    },
    /**
     * Gets the time difference in seconds between now and countdown due date.
     *
     * @private
     */
    _getDelta: function () {
        const currentTimestamp = Date.now() / 1000;
        return this.endTime - currentTimestamp;
    },
    /**
     * Handles the action that should be executed once the countdown ends.
     *
     * @private
     */
    _handleEndCountdownAction: function () {
        if (this.endAction === 'redirect') {
            const redirectUrl = this.el.dataset.redirectUrl || '/';
            if (this.hereBeforeTimerEnds) {
                // Wait a bit, if the landing page has the same publish date
                setTimeout(() => window.location = redirectUrl, 500);
            } else {
                // Show (non editable) msg when user lands on already finished countdown
                if (!this.$('.s_countdown_end_redirect_message').length) {
                    const $container = this.$('> .container, > .container-fluid, > .o_container_small');
                    $container.append(
                        $(renderToElement('website.s_countdown.end_redirect_message', {
                            redirectUrl: redirectUrl,
                        }))
                    );
                }
            }
        } else if (this.endAction === 'message' || this.endAction === 'message_no_countdown') {
            this.$('.s_countdown_end_message').removeClass('d-none');
        }
    },
    /**
     * Initializes the `diff` object. It will contains every visible time unit
     * which will each contain its related canvas, total step, label..
     *
     * @private
     */
    _initTimeDiff: function () {
        const delta = this._getDelta();
        this.diff = [];
        if (this._isUnitVisible('d') && !(this.onlyOneUnit && delta < 86400)) {
            this.diff.push({
                canvas: $('<div class="s_countdown_canvas_flex"><canvas class="w-100"/></div>').appendTo(this.$wrapper)[0],
                // There is no logical number of unit (total) on which day units
                //  can be compared against, so we use an arbitrary number.
                total: 15,
                label: _t("Days"),
                nbSeconds: 86400,
            });
        }
        if (this._isUnitVisible('h') || (this.onlyOneUnit && delta < 86400 && delta > 3600)) {
            this.diff.push({
                canvas: $('<div class="s_countdown_canvas_flex"><canvas class="w-100"/></div>').appendTo(this.$wrapper)[0],
                total: 24,
                label: _t("Hours"),
                nbSeconds: 3600,
            });
        }
        if (this._isUnitVisible('m') || (this.onlyOneUnit && delta < 3600 && delta > 60)) {
            this.diff.push({
                canvas: $('<div class="s_countdown_canvas_flex"><canvas class="w-100"/></div>').appendTo(this.$wrapper)[0],
                total: 60,
                label: _t("Minutes"),
                nbSeconds: 60,
            });
        }
        if (this._isUnitVisible('s') || (this.onlyOneUnit && delta < 60)) {
            this.diff.push({
                canvas: $('<div class="s_countdown_canvas_flex"><canvas class="w-100"/></div>').appendTo(this.$wrapper)[0],
                total: 60,
                label: _t("Seconds"),
                nbSeconds: 1,
            });
        }
    },
    /**
     * Returns weither or not the countdown should be displayed for the given
     * unit (days, sec..).
     *
     * @private
     * @param {string} unit - either 'd', 'm', 'h', or 's'
     * @returns {boolean}
     */
    _isUnitVisible: function (unit) {
        return this.display.includes(unit);
    },
    /**
     * Draws the whole countdown, including one countdown for each time unit.
     *
     * @private
     */
    _render: function () {

        // If only one unit mode, restart widget on unit change to populate diff
        if (this.onlyOneUnit && this._getDelta() < this.diff[0].nbSeconds) {
            this.$('.s_countdown_canvas_flex').remove();
            this._initTimeDiff();
        }
        this._updateTimeDiff();

        const hideCountdown = this.isFinished && !this.editableMode && this.$el.hasClass('hide-countdown');
        if (this.layout === 'text') {
            this.$('.s_countdown_canvas_flex').addClass('d-none');
            if (!this.$textWrapper) {
                this.$textWrapper = $('<span/>').attr({
                    class: 's_countdown_text_wrapper d-none',
                });
                this.$textWrapper.text(_t("Countdown ends in"));
                this.$textWrapper.append($('<span/>').attr({
                    class: 's_countdown_text ms-1',
                }));
                this.$textWrapper.appendTo(this.$wrapper);
            }

            this.$textWrapper.toggleClass('d-none', hideCountdown);

            const countdownText = this.diff.map(e => e.nb + ' ' + e.label).join(', ');
            this.$('.s_countdown_text').text(countdownText.toLowerCase());
        } else {
            for (const val of this.diff) {
                const canvas = val.canvas.querySelector('canvas');
                const ctx = canvas.getContext("2d");
                ctx.canvas.width = this.width;
                ctx.canvas.height = this.size;
                this._clearCanvas(ctx);

                $(canvas).toggleClass('d-none', hideCountdown);
                if (hideCountdown) {
                    continue;
                }

                // Draw canvas elements
                if (this.layoutBackground !== 'none') {
                    this._drawBgShape(ctx, this.layoutBackground === 'plain');
                }
                this._drawText(canvas, val.nb, val.label, this.layoutBackground === 'plain');
                if (this.progressBarStyle === 'surrounded') {
                    this._drawProgressBarBg(ctx, this.progressBarWeight === 'thin');
                }
                if (this.progressBarStyle !== 'none') {
                    this._drawProgressBar(ctx, val.nb, val.total, this.progressBarWeight === 'thin');
                }
                this.$('.s_countdown_canvas_flex').toggleClass('mx-1', this.layout === 'boxes');
            }
        }

        if (this.isFinished) {
            clearInterval(this.setInterval);
            if (!this.editableMode) {
                this._handleEndCountdownAction();
            }
        }
    },
    /**
     * Updates the remaining units into the `diff` object.
     *
     * @private
     */
    _updateTimeDiff: function () {
        let delta = this._getDelta();
        this.isFinished = delta < 0;
        if (this.isFinished) {
            for (const unitData of this.diff) {
                  unitData.nb = 0;
            }
            return;
        }

        this.hereBeforeTimerEnds = true;
        for (const unitData of this.diff) {
              unitData.nb = Math.floor(delta / unitData.nbSeconds);
              delta -= unitData.nb * unitData.nbSeconds;
        }
    },

    //--------------------------------------------------------------------------
    // Canvas drawing methods
    //--------------------------------------------------------------------------

    /**
     * Erases the canvas.
     *
     * @private
     * @param {RenderingContext} ctx - Context of the canvas
     */
    _clearCanvas: function (ctx) {
        ctx.clearRect(0, 0, this.size, this.size);
    },
    /**
     * Draws a text into the canvas.
     *
     * @private
     * @param {HTMLCanvasElement} canvas
     * @param {string} textNb - text to display in the center of the canvas, in big
     * @param {string} textUnit - text to display bellow `textNb` in small
     * @param {boolean} full - if true, the shape will be drawn up to the progressbar
     */
    _drawText: function (canvas, textNb, textUnit, full = false) {
        const ctx = canvas.getContext("2d");
        const nbSize = this.size / 4;
        ctx.font = `${nbSize}px Arial`;
        ctx.fillStyle = this.textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(textNb, canvas.width / 2, canvas.height / 2);

        const unitSize = this.size / 12;
        ctx.font = `${unitSize}px Arial`;
        ctx.fillText(textUnit, canvas.width / 2, canvas.height / 2 + nbSize / 1.5, this.width);

        if (this.layout === 'boxes' && this.layoutBackground !== 'none' && this.progressBarStyle === 'none') {
            let barWidth = this.size / (this.progressBarWeight === 'thin' ? 31 : 10);
            if (full) {
                barWidth = 0;
            }
            ctx.beginPath();
            ctx.moveTo(barWidth, this.size / 2);
            ctx.lineTo(this.width - barWidth, this.size / 2);
            ctx.stroke();
        }
    },
    /**
     * Draws a plain shape into the canvas.
     *
     * @private
     * @param {RenderingContext} ctx - Context of the canvas
     * @param {boolean} full - if true, the shape will be drawn up to the progressbar
     */
    _drawBgShape: function (ctx, full = false) {
        ctx.fillStyle = this.layoutBackgroundColor;
        ctx.beginPath();
        if (this.layout === 'circle') {
            let rayon = this.size / 2;
            if (this.progressBarWeight === 'thin') {
                rayon -= full ? this.size / 29 : this.size / 15;
            } else {
                rayon -= full ? 0 : this.size / 10;
            }
            ctx.arc(this.size / 2, this.size / 2, rayon, 0, Math.PI * 2);
            ctx.fill();
        } else if (this.layout === 'boxes') {
            let barWidth = this.size / (this.progressBarWeight === 'thin' ? 31 : 10);
            if (full) {
                barWidth = 0;
            }

            ctx.fillStyle = this.layoutBackgroundColor;
            ctx.rect(barWidth, barWidth, this.width - barWidth * 2, this.size - barWidth * 2);
            ctx.fill();

            const gradient = ctx.createLinearGradient(0, this.width, 0, 0);
            gradient.addColorStop(0, '#ffffff24');
            gradient.addColorStop(1, this.layoutBackgroundColor);
            ctx.fillStyle = gradient;
            ctx.rect(barWidth, barWidth, this.width - barWidth * 2, this.size - barWidth * 2);
            ctx.fill();
            $(ctx.canvas).css({'border-radius': '8px'});
        }
    },
    /**
     * Draws a progress bar around the countdown shape.
     *
     * @private
     * @param {RenderingContext} ctx - Context of the canvas
     * @param {string} nbUnit - how many unit should fill progress bar
     * @param {string} totalUnit - number of unit to do a complete progress bar
     * @param {boolean} thinLine - if true, the progress bar will be thiner
     */
    _drawProgressBar: function (ctx, nbUnit, totalUnit, thinLine) {
        ctx.strokeStyle = this.progressBarColor;
        ctx.lineWidth = thinLine ? this.size / 35 : this.size / 10;
        if (this.layout === 'circle') {
            ctx.beginPath();
            ctx.arc(this.size / 2, this.size / 2, this.size / 2 - this.size / 20, Math.PI / -2, (Math.PI * 2) * (nbUnit / totalUnit) + (Math.PI / -2));
            ctx.stroke();
        } else if (this.layout === 'boxes') {
            ctx.lineWidth *= 2;
            let pc = nbUnit / totalUnit * 100;

            // Lines: Top(x1,y1,x2,y2) Right(x1,y1,x2,y2) Bottom(x1,y1,x2,y2) Left(x1,y1,x2,y2)
            const linesCoordFuncs = [
                (linePc) => [0 + ctx.lineWidth / 2, 0, (this.width - ctx.lineWidth / 2) * linePc / 25 + ctx.lineWidth / 2, 0],
                (linePc) => [this.width, 0 + ctx.lineWidth / 2, this.width, (this.size - ctx.lineWidth / 2) * linePc / 25 + ctx.lineWidth / 2],
                (linePc) => [this.width - ((this.width - ctx.lineWidth / 2) * linePc / 25) - ctx.lineWidth / 2, this.size, this.width - ctx.lineWidth / 2, this.size],
                (linePc) => [0, this.size - ((this.size - ctx.lineWidth / 2) * linePc / 25) - ctx.lineWidth / 2, 0, this.size - ctx.lineWidth / 2],
            ];
            while (pc > 0 && linesCoordFuncs.length) {
                const linePc = Math.min(pc, 25);
                const lineCoord = (linesCoordFuncs.shift())(linePc);
                ctx.beginPath();
                ctx.moveTo(lineCoord[0], lineCoord[1]);
                ctx.lineTo(lineCoord[2], lineCoord[3]);
                ctx.stroke();
                pc -= linePc;
            }
        }
    },
    /**
     * Draws a full lighter background progressbar around the shape.
     *
     * @private
     * @param {RenderingContext} ctx - Context of the canvas
     * @param {boolean} thinLine - if true, the progress bar will be thiner
     */
    _drawProgressBarBg: function (ctx, thinLine) {
        ctx.strokeStyle = this.progressBarColor;
        ctx.globalAlpha = 0.2;
        ctx.lineWidth = thinLine ? this.size / 35 : this.size / 10;
        if (this.layout === 'circle') {
            ctx.beginPath();
            ctx.arc(this.size / 2, this.size / 2, this.size / 2 - this.size / 20, 0, Math.PI * 2);
            ctx.stroke();
        } else if (this.layout === 'boxes') {
            ctx.lineWidth *= 2;

            // Lines: Top(x1,y1,x2,y2) Right(x1,y1,x2,y2) Bottom(x1,y1,x2,y2) Left(x1,y1,x2,y2)
            const points = [
                [0 + ctx.lineWidth / 2, 0, this.width, 0],
                [this.width, 0 + ctx.lineWidth / 2, this.width, this.size],
                [0, this.size, this.width - ctx.lineWidth / 2, this.size],
                [0, 0, 0, this.size - ctx.lineWidth / 2],
            ];
            while (points.length) {
                const point = points.shift();
                ctx.beginPath();
                ctx.moveTo(point[0], point[1]);
                ctx.lineTo(point[2], point[3]);
                ctx.stroke();
            }
        }
        ctx.globalAlpha = 1;
    },
});

publicWidget.registry.countdown = CountdownWidget;

export default CountdownWidget;
