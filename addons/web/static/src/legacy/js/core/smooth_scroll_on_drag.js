odoo.define('web/static/src/js/core/smooth_scroll_on_drag.js', function (require) {
"use strict";

const Class = require('web.Class');
const mixins = require('web.mixins');

/**
 * Provides a helper for SmoothScrollOnDrag options.offsetElements
 */
const OffsetElementsHelper = Class.extend({

    /**
     * @constructor
     * @param {Object} offsetElements
     * @param {jQuery} [offsetElements.$top] top offset element
     * @param {jQuery} [offsetElements.$right] right offset element
     * @param {jQuery} [offsetElements.$bottom] bottom offset element
     * @param {jQuery} [offsetElements.$left] left offset element
     */
    init: function (offsetElements) {
        this.offsetElements = offsetElements;
    },
    top: function () {
        if (!this.offsetElements.$top || !this.offsetElements.$top.length) {
            return 0;
        }
        return this.offsetElements.$top.get(0).getBoundingClientRect().bottom;
    },
    right: function () {
        if (!this.offsetElements.$right || !this.offsetElements.$right.length) {
            return 0;
        }
        return this.offsetElements.$right.get(0).getBoundingClientRect().left;
    },
    bottom: function () {
        if (!this.offsetElements.$bottom || !this.offsetElements.$bottom.length) {
            return 0;
        }
        return this.offsetElements.$bottom.get(0).getBoundingClientRect().top;
    },
    left: function () {
        if (!this.offsetElements.$left || !this.offsetElements.$left.length) {
            return 0;
        }
        return this.offsetElements.$left.get(0).getBoundingClientRect().right;
    },
});

/**
 * Provides smooth scroll behaviour on drag.
 */
const SmoothScrollOnDrag = Class.extend(mixins.ParentedMixin, {

    /**
     * @constructor
     * @param {Object} parent The parent widget that uses this class.
     * @param {jQuery} $element The element the smooth scroll on drag has to be set on.
     * @param {jQuery} $scrollTarget The element the scroll will be triggered on.
     * @param {Object} [options={}]
     * @param {Object} [options.jQueryDraggableOptions={}] The configuration to be passed to
     *        the jQuery draggable function (all will be passed except scroll which will
     *        be overridden to false).
     * @param {Number} [options.scrollOffsetThreshold=150] (Integer) The distance from the
     *        bottom/top of the options.$scrollTarget from which the smooth scroll will be
     *        triggered.
     * @param {Number} [options.scrollStep=20] (Integer) The step of the scroll.
     * @param {Number} [options.scrollTimerInterval=5] (Integer) The interval (in ms) the
     *        scrollStep will be applied.
     * @param {Object} [options.scrollBoundaries = {}] Specifies whether scroll can still be triggered
     *        when dragging $element outside of target.
     * @param {Object} [options.scrollBoundaries.top = true] Specifies whether scroll can still be triggered
     *        when dragging $element above the top edge of target.
     * @param {Object} [options.scrollBoundaries.right = true] Specifies whether scroll can still be triggered
     *        when dragging $element after the right edge of target.
     * @param {Object} [options.scrollBoundaries.bottom = true] Specifies whether scroll can still be triggered
     *        when dragging $element bellow the bottom edge of target.
     * @param {Object} [options.scrollBoundaries.left = true] Specifies whether scroll can still be triggered
     *        when dragging $element before the left edge of target.
     * @param {Object} [options.offsetElements={}] Visible elements in $scrollTarget that
     *        reduce $scrollTarget drag visible area (scroll will be triggered sooner than
     *        normally). A selector is passed so that elements such as automatically hidden
     *        menu can then be correctly handled.
     * @param {jQuery} [options.offsetElements.$top] Visible top offset element which height will
     *        be taken into account when triggering scroll at the top of the $scrollTarget.
     * @param {jQuery} [options.offsetElements.$right] Visible right offset element which width
     *        will be taken into account when triggering scroll at the right side of the
     *        $scrollTarget.
     * @param {jQuery} [options.offsetElements.$bottom] Visible bottom offset element which height
     *        will be taken into account when triggering scroll at bottom of the $scrollTarget.
     * @param {jQuery} [options.offsetElements.$left] Visible left offset element which width
     *        will be taken into account when triggering scroll at the left side of the
     *        $scrollTarget.
     * @param {boolean} [options.disableHorizontalScroll = false] Disable horizontal scroll if not needed.
     */
    init(parent, $element, $scrollTarget, options = {}) {
        mixins.ParentedMixin.init.call(this);
        this.setParent(parent);

        this.$element = $element;
        this.$scrollTarget = $scrollTarget;
        this.options = options;

        // Setting optional options to their default value if not provided
        this.options.jQueryDraggableOptions = this.options.jQueryDraggableOptions || {};
        if (!this.options.jQueryDraggableOptions.cursorAt) {
            this.$element.on('mousedown.smooth_scroll', this._onElementMouseDown.bind(this));
        }
        this.options.scrollOffsetThreshold = this.options.scrollOffsetThreshold || 150;
        this.options.scrollStep = this.options.scrollStep || 20;
        this.options.scrollTimerInterval = this.options.scrollTimerInterval || 5;
        this.options.offsetElements = this.options.offsetElements || {};
        this.options.offsetElementsManager = new OffsetElementsHelper(this.options.offsetElements);
        this.options.scrollBoundaries = Object.assign({
            top: true,
            right: true,
            bottom: true,
            left: true
        }, this.options.scrollBoundaries);

        this.autoScrollHandler = null;

        this.scrollStepDirectionEnum = {
            up: -1,
            right: 1,
            down: 1,
            left: -1,
        };

        this.options.jQueryDraggableOptions.scroll = false;
        this.options.disableHorizontalScroll = this.options.disableHorizontalScroll || false;
        const draggableOptions = Object.assign({}, this.options.jQueryDraggableOptions, {
            start: (ev, ui) => this._onSmoothDragStart(ev, ui, this.options.jQueryDraggableOptions.start),
            drag: (ev, ui) => this._onSmoothDrag(ev, ui, this.options.jQueryDraggableOptions.drag),
            stop: (ev, ui) => this._onSmoothDragStop(ev, ui, this.options.jQueryDraggableOptions.stop),
        });
        this.$element.draggable(draggableOptions);
    },
    /**
     * @override
     */
    destroy: function () {
        mixins.ParentedMixin.destroy.call(this);
        this.$element.off('.smooth_scroll');
        this._stopSmoothScroll();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Starts the scroll process using the options.
     * The options will be updated dynamically when the handler _onSmoothDrag
     * will be called. The interval will be cleared when the handler
     * _onSmoothDragStop will be called.
     *
     * @private
     * @param {Object} ui The jQuery drag handler ui parameter.
     */
    _startSmoothScroll(ui) {
        this._stopSmoothScroll();
        this.autoScrollHandler = setInterval(
            () => {
                // Prevents Delta's from being different from 0 when scroll should not occur (except when
                // helper is dragged outside of this.$scrollTarget's visible area as it increases
                // this.$scrollTarget's scrollHeight).
                // Also, this code prevents the helper from being incorrectly repositioned when target is
                // a child of this.$scrollTarget.
                this.verticalDelta = Math.min(
                    // Ensures scrolling stops when dragging bellow this.$scrollTarget bottom.
                    Math.max(
                        0,
                        this.$scrollTarget.get(0).scrollHeight
                        - (this.$scrollTarget.scrollTop() + this.$scrollTarget.innerHeight())
                    ),
                    // Ensures scrolling stops when dragging above this.$scrollTarget top.
                    Math.max(
                        this.verticalDelta,
                        -this.$scrollTarget.scrollTop()
                    )
                );
                this.horizontalDelta = Math.min(
                    //Ensures scrolling stops when dragging left to this.$scrollTarget.
                    Math.max(
                        0,
                        this.$scrollTarget.get(0).scrollWidth
                        - (this.$scrollTarget.scrollLeft() + this.$scrollTarget.innerWidth())
                    ),
                    //Ensures scrolling stops when dragging right to this.$scrollTarget.
                    Math.max(
                        this.horizontalDelta,
                        -this.$scrollTarget.scrollLeft()
                    )
                );

                // Keep helper at right position while scrolling when helper is a child of this.$scrollTarget.
                if (this.scrollTargetIsParent) {
                    const offset = ui.helper.offset();
                    ui.helper.offset({
                        top: offset.top + this.verticalDelta,
                        left: offset.left + this.horizontalDelta
                    });
                }
                this.$scrollTarget.scrollTop(
                    this.$scrollTarget.scrollTop() +
                    this.verticalDelta
                );
                if (!this.options.disableHorizontalScroll) {
                    this.$scrollTarget.scrollLeft(
                        this.$scrollTarget.scrollLeft() +
                        this.horizontalDelta
                    );
                }
            },
            this.options.scrollTimerInterval
        );
    },
    /**
     * Stops the scroll process if any is running.
     *
     * @private
     */
    _stopSmoothScroll() {
        clearInterval(this.autoScrollHandler);
    },
    /**
     * Updates the options depending on the offset position of the draggable
     * helper. In the same time options are used by an interval to trigger
     * scroll behaviour.
     * @see {@link _startSmoothScroll} for interval implementation details.
     *
     * @private
     * @param {Object} ui The jQuery drag handler ui parameter.
     */
    _updatePositionOptions(ui) {
        const draggableHelperOffset = ui.offset;
        const scrollTargetOffset = this.$scrollTarget.offset();
        let visibleOffset = {
            top: draggableHelperOffset.top
                - scrollTargetOffset.top
                + this.options.jQueryDraggableOptions.cursorAt.top
                - this.options.offsetElementsManager.top(),
            right: scrollTargetOffset.left + this.$scrollTarget.outerWidth()
                - draggableHelperOffset.left
                - this.options.jQueryDraggableOptions.cursorAt.left
                - this.options.offsetElementsManager.right(),
            bottom: scrollTargetOffset.top + this.$scrollTarget.outerHeight()
                - draggableHelperOffset.top
                - this.options.jQueryDraggableOptions.cursorAt.top
                - this.options.offsetElementsManager.bottom(),
            left: draggableHelperOffset.left
                - scrollTargetOffset.left
                + this.options.jQueryDraggableOptions.cursorAt.left
                - this.options.offsetElementsManager.left(),
        };

        if (this.iframeOffset) {
            const { x, y } = this.iframeOffset;
            visibleOffset.left -= x;
            visibleOffset.top -= y;
            visibleOffset.bottom += y;
            visibleOffset.right += x;
        }

        // If this.$scrollTarget is the html tag, we need to take the scroll position in to account
        // as offsets positions are calculated relative to the document (thus <html>).
        if (this.scrollTargetIsDocument) {
            const scrollTargetScrollTop = this.$scrollTarget.scrollTop();
            const scrollTargetScrollLeft = this.$scrollTarget.scrollLeft();
            visibleOffset.top -= scrollTargetScrollTop;
            visibleOffset.right += scrollTargetScrollLeft;
            visibleOffset.bottom += scrollTargetScrollTop;
            visibleOffset.left -= scrollTargetScrollLeft;
        }

        const scrollDecelerator = {
            vertical: 0,
            horizontal: 0,
        };

        const scrollStepDirection = {
            vertical: this.scrollStepDirectionEnum.down,
            horizontal: this.scrollStepDirectionEnum.right,
        };

        // Prevent scroll if outside of scroll boundaries
        if ((!this.options.scrollBoundaries.top && visibleOffset.top < 0) ||
            (!this.options.scrollBoundaries.right && visibleOffset.right < 0) ||
            (!this.options.scrollBoundaries.bottom && visibleOffset.bottom < 0) ||
            (!this.options.scrollBoundaries.left && visibleOffset.left < 0)) {
                scrollDecelerator.horizontal = 1;
                scrollDecelerator.vertical = 1;
        } else {
            // Manage vertical scroll
            if (visibleOffset.bottom <= this.options.scrollOffsetThreshold) {
                scrollDecelerator.vertical = Math.max(0, visibleOffset.bottom)
                                           / this.options.scrollOffsetThreshold;
            } else if (visibleOffset.top <= this.options.scrollOffsetThreshold) {
                scrollDecelerator.vertical = Math.max(0, visibleOffset.top)
                                           / this.options.scrollOffsetThreshold;
                scrollStepDirection.vertical = this.scrollStepDirectionEnum.up;
            } else {
                scrollDecelerator.vertical = 1;
            }

            // Manage horizontal scroll
            if (visibleOffset.right <= this.options.scrollOffsetThreshold) {
                scrollDecelerator.horizontal = Math.max(0, visibleOffset.right)
                                             / this.options.scrollOffsetThreshold;
            } else if (visibleOffset.left <= this.options.scrollOffsetThreshold) {
                scrollDecelerator.horizontal = Math.max(0, visibleOffset.left)
                                             / this.options.scrollOffsetThreshold;
                scrollStepDirection.horizontal = this.scrollStepDirectionEnum.left;
            } else {
                scrollDecelerator.horizontal = 1;
            }
        }

        this.verticalDelta = Math.ceil(scrollStepDirection.vertical *
            this.options.scrollStep *
            (1 - Math.sqrt(scrollDecelerator.vertical)));
        this.horizontalDelta = Math.ceil(scrollStepDirection.horizontal *
            this.options.scrollStep *
            (1 - Math.sqrt(scrollDecelerator.horizontal)));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when mouse button is down on this.$element.
     * Updates the mouse cursor position variable.
     *
     * @private
     * @param {Object} ev The jQuery mousedown handler event parameter.
     */
    _onElementMouseDown(ev) {
        const elementOffset = $(ev.target).offset();
        this.options.jQueryDraggableOptions.cursorAt = {
            top: ev.pageY - elementOffset.top,
            left: ev.pageX - elementOffset.left,
        };
    },
    /**
     * Called when dragging the element.
     * Updates the position options and call the provided callback if any.
     *
     * @private
     * @param {Object} ev The jQuery drag handler event parameter.
     * @param {Object} ui The jQuery drag handler ui parameter.
     * @param {Function} onDragCallback The jQuery drag callback.
     */
    _onSmoothDrag(ev, ui, onDragCallback) {
        this._updatePositionOptions(ui);
        if (typeof onDragCallback === 'function') {
            onDragCallback.call(ui.helper, ev, ui);
        }
    },
    /**
     * Called when starting to drag the element.
     * Updates the position params, starts smooth scrolling process and call the
     * provided callback if any.
     *
     * @private
     * @param {Object} ev The jQuery drag handler event parameter.
     * @param {Object} ui The jQuery drag handler ui parameter.
     * @param {Function} onDragStartCallBack The jQuery drag callback.
     */
    _onSmoothDragStart(ev, ui, onDragStartCallBack) {
        this.scrollTargetIsDocument = this.$scrollTarget.is('html');
        this.iframeOffset = this.$scrollTarget[0].ownerDocument.defaultView.frameElement && this.$scrollTarget[0].ownerDocument.defaultView.frameElement.getBoundingClientRect();
        this.scrollTargetIsParent = this.$scrollTarget.get(0).contains(this.$element.get(0));
        this._updatePositionOptions(ui);
        this._startSmoothScroll(ui);
        if (typeof onDragStartCallBack === 'function') {
            onDragStartCallBack.call(ui.helper, ev, ui);
        }
    },
    /**
     * Called when stopping to drag the element.
     * Stops the smooth scrolling process and call the provided callback if any.
     *
     * @private
     * @param {Object} ev The jQuery drag handler event parameter.
     * @param {Object} ui The jQuery drag handler ui parameter.
     * @param {Function} onDragEndCallBack The jQuery drag callback.
     */
    _onSmoothDragStop(ev, ui, onDragEndCallBack) {
        this._stopSmoothScroll();
        if (typeof onDragEndCallBack === 'function') {
            onDragEndCallBack.call(ui.helper, ev, ui);
        }
    },
});

return SmoothScrollOnDrag;
});
