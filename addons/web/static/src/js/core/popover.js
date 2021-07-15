odoo.define('web.Popover', function (require) {
    'use strict';

    const patchMixin = require('web.patchMixin');

    const { Component, hooks, misc, QWeb } = owl;
    const { Portal } = misc;
    const { useRef, useState } = hooks;

    /**
     * Popover
     *
     * Represents a bootstrap-style popover handled with pure JS. The popover
     * will be visually bound to its `target` using an arrow-like '::before'
     * CSS pseudo-element.
     * @extends Component
     **/
    class Popover extends Component {
        /**
         * @param {Object} props
         * @param {String} [props.position='bottom']
         * @param {String} [props.title]
         */
        constructor() {
            super(...arguments);
            this.popoverRef = useRef('popover');
            this.orderedPositions = ['top', 'bottom', 'left', 'right'];
            this.state = useState({
                displayed: false,
            });

            this._onClickDocument = this._onClickDocument.bind(this);
            this._onScrollDocument = this._onScrollDocument.bind(this);
            this._onResizeWindow = this._onResizeWindow.bind(this);

            this._onScrollDocument = _.throttle(this._onScrollDocument, 50);
            this._onResizeWindow = _.debounce(this._onResizeWindow, 250);

            /**
             * Those events are only necessary if the popover is currently open,
             * so we decided for performance reasons to avoid binding them while
             * it is closed. This allows to have many popover instantiated while
             * keeping the count of global handlers low.
             */
            this._hasGlobalEventListeners = false;
        }

        mounted() {
            this._compute();
        }

        patched() {
            this._compute();
        }

        willUnmount() {
            if (this._hasGlobalEventListeners) {
                this._removeGlobalEventListeners();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _addGlobalEventListeners() {
            /**
             * Use capture for the following events to ensure no other part of
             * the code can stop its propagation from reaching here.
             */
            document.addEventListener('click', this._onClickDocument, {
                capture: true,
            });
            document.addEventListener('scroll', this._onScrollDocument, {
                capture: true,
            });
            window.addEventListener('resize', this._onResizeWindow);
            this._hasGlobalEventListeners = true;
        }

        _close() {
            this.state.displayed = false;
        }

        /**
         * Computes the popover according to its props. This method will try to position the
         * popover as requested (according to the `position` props). If the requested position
         * does not fit the viewport, other positions will be tried in a clockwise order starting
         * a the requested position (e.g. starting from left: top, right, bottom). If no position
         * is found that fits the viewport, 'bottom' is used.
         *
         * @private
         */
        _compute() {
            if (!this._hasGlobalEventListeners && this.state.displayed) {
                this._addGlobalEventListeners();
            }
            if (this._hasGlobalEventListeners && !this.state.displayed) {
                this._removeGlobalEventListeners();
            }
            if (!this.state.displayed) {
                return;
            }

            // copy the default ordered position to avoid updating them in place
            const possiblePositions = [...this.orderedPositions];
            const positionIndex = possiblePositions.indexOf(
                this.props.position
            );

            const positioningData = this.constructor.computePositioningData(
                this.popoverRef.el,
                this.el
            );

            // check if the requested position fits the viewport; if not,
            // try all other positions and find one that does
            const position = possiblePositions
                .slice(positionIndex)
                .concat(possiblePositions.slice(0, positionIndex))
                .map((pos) => positioningData[pos])
                .find((pos) => {
                    this.popoverRef.el.style.top = `${pos.top}px`;
                    this.popoverRef.el.style.left = `${pos.left}px`;
                    const rect = this.popoverRef.el.getBoundingClientRect();
                    const html = document.documentElement;
                    return (
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.bottom <= (window.innerHeight || html.clientHeight) &&
                        rect.right <= (window.innerWidth || html.clientWidth)
                    );
                });

            // remove all existing positioning classes
            possiblePositions.forEach((pos) => {
                this.popoverRef.el.classList.remove(`o_popover--${pos}`);
            });

            if (position) {
                // apply the preferred found position that fits the viewport
                this.popoverRef.el.classList.add(`o_popover--${position.name}`);
            } else {
                // use the given `position` props because no position fits
                this.popoverRef.el.style.top = `${positioningData[this.props.position].top}px`;
                this.popoverRef.el.style.left = `${positioningData[this.props.position].left}px`;
                this.popoverRef.el.classList.add(`o_popover--${this.props.position}`);
            }
        }

        /**
         * @private
         */
        _removeGlobalEventListeners() {
            document.removeEventListener('click', this._onClickDocument, true);
            document.removeEventListener('scroll', this._onScrollDocument, true);
            window.removeEventListener('resize', this._onResizeWindow);
            this._hasGlobalEventListeners = false;
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Toggles the popover depending on its current state.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClick(ev) {
            this.state.displayed = !this.state.displayed;
        }

        /**
         * A click outside the popover will dismiss the current popover.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickDocument(ev) {
            // Handled by `_onClick`.
            if (this.el.contains(ev.target)) {
                return;
            }
            // Ignore click inside the popover.
            if (this.popoverRef.el && this.popoverRef.el.contains(ev.target)) {
                return;
            }
            this._close();
        }

        /**
         * @private
         * @param {Event} ev
         */
        _onPopoverClose(ev) {
            this._close();
        }

        /**
         * Popover must recompute its position when children content changes.
         *
         * @private
         * @param {Event} ev
         */
        _onPopoverCompute(ev) {
            this._compute();
        }

        /**
         * A resize event will need to 'reposition' the popover close to its
         * target.
         *
         * @private
         * @param {Event} ev
         */
        _onResizeWindow(ev) {
            if (this.__owl__.status === 5 /* destroyed */) {
                return;
            }
            this._compute();
        }

        /**
         * A scroll event will need to 'reposition' the popover close to its
         * target.
         *
         * @private
         * @param {Event} ev
         */
        _onScrollDocument(ev) {
            if (this.__owl__.status === 5 /* destroyed */) {
                return;
            }
            this._compute();
        }

        //----------------------------------------------------------------------
        // Static
        //----------------------------------------------------------------------

        /**
         * Compute the expected positioning coordinates for each possible
         * positioning based on the target and popover sizes.
         * In particular the popover must not overflow the viewport in any
         * direction, it should actually stay at `margin` distance from the
         * border to look good.
         *
         * @static
         * @param {HTMLElement} popoverElement The popover element
         * @param {HTMLElement} targetElement The target element, to which
         *  the popover will be visually 'bound'
         * @param {integer} [margin=16] Minimal accepted margin from the border
         *  of the viewport.
         * @returns {Object}
         */
        static computePositioningData(popoverElement, targetElement, margin = 16) {
            // set target position, possible position
            const boundingRectangle = targetElement.getBoundingClientRect();
            const targetTop = boundingRectangle.top;
            const targetLeft = boundingRectangle.left;
            const targetHeight = targetElement.offsetHeight;
            const targetWidth = targetElement.offsetWidth;
            const popoverHeight = popoverElement.offsetHeight;
            const popoverWidth = popoverElement.offsetWidth;
            const windowWidth = window.innerWidth || document.documentElement.clientWidth;
            const windowHeight = window.innerHeight || document.documentElement.clientHeight;
            const leftOffsetForVertical = Math.max(
                margin,
                Math.min(
                    Math.round(targetLeft - (popoverWidth - targetWidth) / 2),
                    windowWidth - popoverWidth - margin,
                ),
            );
            const topOffsetForHorizontal = Math.max(
                margin,
                Math.min(
                    Math.round(targetTop - (popoverHeight - targetHeight) / 2),
                    windowHeight - popoverHeight - margin,
                ),
            );
            return {
                top: {
                    name: 'top',
                    top: Math.round(targetTop - popoverHeight),
                    left: leftOffsetForVertical,
                },
                right: {
                    name: 'right',
                    top: topOffsetForHorizontal,
                    left: Math.round(targetLeft + targetWidth),
                },
                bottom: {
                    name: 'bottom',
                    top: Math.round(targetTop + targetHeight),
                    left: leftOffsetForVertical,
                },
                left: {
                    name: 'left',
                    top: topOffsetForHorizontal,
                    left: Math.round(targetLeft - popoverWidth),
                },
            };
        }

    }

    Popover.components = { Portal };
    Popover.template = 'Popover';
    Popover.defaultProps = {
        position: 'bottom',
    };
    Popover.props = {
        position: {
            type: String,
            validate: (p) => ['top', 'bottom', 'left', 'right'].includes(p),
        },
        title: { type: String, optional: true },
    };

    QWeb.registerComponent('Popover', Popover);

    return patchMixin(Popover);
});
