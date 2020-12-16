odoo.define('web/static/src/js/core/smooth_scroll_on_drag.js', function (require) {
"use strict";

const Class = require('web.Class');
const mixins = require('web.mixins');

/**
 * Provides smooth scroll behaviour on drag.
 */
const SmoothScrollOnDrag = Class.extend(mixins.ParentedMixin, {

    /**
     * @constructor
     * @param {Object} parent The parent widget that uses this class.
     * @param {jQuery} $element The element the smooth scroll on drag has to be set on.
     * @param {jQuery} $container Container for drop element.
     *        scrollTarget will be found with the closest scrollable parents.
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
     * @param {Function<jQuery>} [options.dropzones] Function must return a JQuery list of dropzone elements.
     * @param {Function<ui, droppable>} [options.over] Callback triggered when the draggable element is
     *         over a dropzone (requiered with options.dropzones).
     * @param {Function<ui, droppable>} [options.out] Callback triggered when the draggable element is
     *         no longer above the dropzone (requiered with options.dropzones).
     */
    init(parent, $element, $container, options = {}) {
        mixins.ParentedMixin.init.call(this);
        this.setParent(parent);

        this.$element = $element;
        this.$container = $container;
        this.options = options;

        // Setting optional options to their default value if not provided
        this.options.jQueryDraggableOptions = this.options.jQueryDraggableOptions || {};
        this.options.scrollOffsetThreshold = this.options.scrollOffsetThreshold || 150;
        this.options.scrollStep = this.options.scrollStep || 20;
        this.options.scrollTimerInterval = this.options.scrollTimerInterval || 16;
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
        const draggableOptions = Object.assign({}, this.options.jQueryDraggableOptions, {
            start: (ev, ui) => this._onSmoothDragStart(ev, ui, this.options.jQueryDraggableOptions.start),
            drag: (ev, ui, inst) => this._onSmoothDrag(ev, ui, this.options.jQueryDraggableOptions.drag),
            stop: (ev, ui, inst) => this._onSmoothDragStop(ev, ui, this.options.jQueryDraggableOptions.stop),
        });
        this.$element.draggable(draggableOptions);
    },
    /**
     * @override
     */
    destroy: function () {
        mixins.ParentedMixin.destroy.call(this);
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
                for (const scrollTarget of this.scrollableTargets) {
                    this._smoothScroll(ui, scrollTarget);
                }
            },
            this.options.scrollTimerInterval,
        );
    },
    _smoothScroll(ui, scrollTarget) {
        const delta = this.deltaScrollableTargets.get(scrollTarget);
        // Prevents Delta's from being different from 0 when scroll should not occur (except when
        // helper is dragged outside of scrollTarget's visible area as it increases
        // scrollTarget's scrollHeight).
        // Also, this code prevents the helper from being incorrectly repositioned when target is
        // a child of scrollTarget.
        delta.vertical = Math.min(
            // Ensures scrolling stops when dragging bellow scrollTarget bottom.
            Math.max( 0, scrollTarget.scrollHeight - (scrollTarget.scrollTop + scrollTarget.clientHeight)),
            // Ensures scrolling stops when dragging above scrollTarget top.
            Math.max(delta.vertical, - scrollTarget.scrollTop)
        );
        delta.horizontal = Math.min(
            //Ensures scrolling stops when dragging left to scrollTarget.
            Math.max(0, scrollTarget.scrollWidth - (scrollTarget.scrollLeft + scrollTarget.clientWidth)),
            //Ensures scrolling stops when dragging right to scrollTarget.
            Math.max(delta.horizontal, - scrollTarget.scrollLeft)
        );

        // Keep helper at right position while scrolling when helper is a child of scrollTarget.
        const scrollTargetIsParent = scrollTarget.contains(this.$element.get(0));
        if (scrollTargetIsParent) {
            ui.helper.css({
                'margin-left': parseInt(ui.helper.css('margin-left') || 0) + delta.horizontal,
                'margin-top': parseInt(ui.helper.css('margin-top') || 0) + delta.vertical,
            });
        }
        scrollTarget.scrollTo(
            scrollTarget.scrollLeft + delta.horizontal,
            scrollTarget.scrollTop + delta.vertical,
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
    _getPositionDelta(ui, scrollTarget) {
        const $scrollTarget = $(scrollTarget);
        const scrollTargetIsDocument = $scrollTarget.is('html, body');
        const draggableHelperOffset = ui.helper[0].getBoundingClientRect();
        const scrollTargetOffset = scrollTarget.getBoundingClientRect();

        let visibleOffset = {
            top: draggableHelperOffset.top
                - scrollTargetOffset.top
                + this.options.jQueryDraggableOptions.cursorAt.top,
            right: scrollTargetOffset.left
                + scrollTarget.clientWidth
                - draggableHelperOffset.left
                - this.options.jQueryDraggableOptions.cursorAt.right,
            bottom: scrollTargetOffset.top
                + scrollTarget.clientHeight
                - draggableHelperOffset.top
                - this.options.jQueryDraggableOptions.cursorAt.bottom,
            left: draggableHelperOffset.left
                - scrollTargetOffset.left
                + this.options.jQueryDraggableOptions.cursorAt.left,
        };

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

        return {
            vertical: Math.ceil(scrollStepDirection.vertical *
                this.options.scrollStep *
                (1 - Math.sqrt(scrollDecelerator.vertical))),
            horizontal: Math.ceil(scrollStepDirection.horizontal *
                this.options.scrollStep *
                (1 - Math.sqrt(scrollDecelerator.horizontal))),
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when dragging the element.
     * Updates the position options and call the provided callback if any.
     * When use dropzones options, call 'over' option when the helper is
     * over a dropzone and call 'out' when the helper is no longer above
     * the dropzone.
     *
     * @private
     * @param {Object} ev The jQuery drag handler event parameter.
     * @param {Object} ui The jQuery drag handler ui parameter.
     * @param {Function} onDragCallback The jQuery drag callback.
     */
    _onSmoothDrag(ev, ui, onDragCallback) {
        for (const scrollTarget of this.scrollableTargets) {
            const delta = this._getPositionDelta(ui, scrollTarget);
            this.deltaScrollableTargets.set(scrollTarget, delta);
        }

        if (typeof onDragCallback === 'function') {
            onDragCallback.call(ui.helper, ev, ui);
        }

        if (this.options.dropzones) {
            if (!this.$dropzones) {
                this.$dropzones = this.options.dropzones.call(ui.helper, ev, ui).filter(function () {
                    if (ui.helper[0].contains(this)) {
                        console.warn('One drop zone is include inside the draggable item.');
                    } else {
                        return true;
                    }
                });
            }
            if (!this.$dropzones.length) {
                return;
            }
            const draggableBox = ui.helper[0].getBoundingClientRect();

            let over;
            for (const zone of this.$dropzones.get()) {
                let box;
                if (this.overDropzone && this.overDropzone[0] === zone) {
                    box = this.overDropzone[1];
                } else {
                    box = zone.getBoundingClientRect();
                }
                if (box.top < draggableBox.top + draggableBox.height && box.top + box.height > draggableBox.top &&
                    box.left < draggableBox.left + draggableBox.width && box.left + box.width > draggableBox.left) {
                    over = zone;
                    break;
                }
            }
            if (this.overDropzone && this.overDropzone[0] !== over) {
                this.options.out.call(ui.helper, ui, this.overDropzone[0]);
                this.overDropzone = null;
            }
            if (over && !this.overDropzone) {
                const box = over.getBoundingClientRect();
                this.overDropzone = [over, {
                    top: box.top,
                    height: box.height,
                    left: box.left,
                    width: box.width,
                }];
                this.options.over.call(ui.helper, ui, over);
            }
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
        const elementOffset = ev.target.getBoundingClientRect();
        this.options.jQueryDraggableOptions.cursorAt = {
            top: ev.pageY - elementOffset.top,
            right: elementOffset.right - ev.pageX,
            bottom: elementOffset.bottom - ev.pageY,
            left: ev.pageX - elementOffset.left,
        };

        this.scrollableTargets = [];
        this.deltaScrollableTargets = new WeakMap();
        let scrollTarget = this.$container[0];
        while (scrollTarget) {
            if (scrollTarget.nodeType === 1 && scrollTarget.scrollHeight > scrollTarget.clientHeight) {
                const overflow = window.getComputedStyle(scrollTarget).overflow;
                if (overflow.includes('auto') || overflow.includes('scroll')) {
                    this.scrollableTargets.push(scrollTarget);
                    this.deltaScrollableTargets.set(scrollTarget, {
                        vertical: 0,
                        horizontal: 0,
                    });
                }
            }
            scrollTarget = scrollTarget.parentNode;
            if (scrollTarget && scrollTarget.nodeType === Node.DOCUMENT_FRAGMENT_NODE && scrollTarget.host) {
                scrollTarget = scrollTarget.host;
            }
        }

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
        this.$dropzones = null;
        this.overDropzone = null;
    },
});

return SmoothScrollOnDrag;
});
