odoo.define('web.Popover', function () {
    'use strict';

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
         * @param {String} props.position='bottom' 'top', 'bottom', 'left' or 'right'
         * @param {String} [props.title]
         */
        constructor() {
            super(...arguments);
            this.popoverRef = useRef('popover');
            this.orderedPositions = ['top', 'right', 'bottom', 'left'];
            this.state = useState({
                displayed: false,
            });
        }

        patched() {
            super.patched(...arguments);
            this.show();
        }

        /**
         * Show the popover according to its props. This method will try to position the
         * popover as requested (according to the `position` props). If the requested position
         * does not fit the viewport, other positions will be tried in a clockwise order starting
         * a the requested position (e.g. starting from left: top, right, bottom). If no position
         * is found that fits the viewport, 'bottom' is used.
         */
        show() {
            if (!this.state.displayed) {
                return;
            }
            // get the target from the dom
            // we don't want to do this early, since the target might not
            // be in the dom when the component is instanciated
            if (!this.constructor._isInViewport(this.el)) {
                // target is no longer in the viewport, close the popover
                return this._close();
            }

            const positionIndex = this.orderedPositions.indexOf(
                this.props.position
            );

            const positioningData = this.constructor._computePositioningData(
                this.popoverRef.el,
                this.el
            );

            // check if the requested position fits the viewport; if not,
            // try all other positions and find one that does
            const position = this.orderedPositions
                .slice(positionIndex)
                .concat(this.orderedPositions.slice(0, positionIndex))
                .map((pos) => positioningData[pos])
                .find((pos) => {
                    this.popoverRef.el.style.top = `${pos.top}px`;
                    this.popoverRef.el.style.left = `${pos.left}px`;
                    return this.constructor._isInViewport(this.popoverRef.el);
                });

            // remove all positioning classes
            this.orderedPositions.forEach((pos) => {
                this.popoverRef.el.classList.remove(`o_popover--${pos}`);
            });

            // apply the found position ('position' props or another position
            // that fits the viewport) if it fits the viewport, otherwise
            // fallback to 'bottom' if no position fits the viewport
            if (position) {
                this.popoverRef.el.classList.add(`o_popover--${position.name}`);
            } else {
                this.popoverRef.el.style.top = `${positioningData.bottom.top}px`;
                this.popoverRef.el.style.left = `${positioningData.bottom.left}px`;
                this.popoverRef.el.classList.add(`o_popover--bottom`);
            }
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _close() {
            this.state.displayed = false;
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Call the static method to display the popover, ensuring all others
         * popover are closed first. This prevents having more than one popover
         * open at a time.
         * @param {DOMEvent} e
         */
        openPopover(e) {
            this.constructor.display(this);
        }

        //--------------------------------------------------------------------------
        // Static
        //--------------------------------------------------------------------------

        /**
         * Compute the expected positioning coordinates for each possible
         * positioning based on the target and popover sizes.
         * @private
         * @static
         * @param {HTMLElement} popoverElement The popover element
         * @param {HTMLElement} targetElement The target element, to which
         *  the popover will be visually 'bound'
         * @returns {Object}
         */
        static _computePositioningData(popoverElement, targetElement) {
            const boundingRectangle = targetElement.getBoundingClientRect();
            const targetTop = boundingRectangle.top;
            const targetLeft = boundingRectangle.left;
            const targetHeight = targetElement.offsetHeight;
            const targetWidth = targetElement.offsetWidth;
            const popoverHeight = popoverElement.offsetHeight;
            const popoverWidth = popoverElement.offsetWidth;
            return {
                top: {
                    name: 'top',
                    top: targetTop - popoverHeight,
                    left: targetLeft - (popoverWidth - targetWidth) / 2,
                },
                right: {
                    name: 'right',
                    top: targetTop - (popoverHeight - targetHeight) / 2,
                    left: targetLeft + targetWidth,
                },
                bottom: {
                    name: 'bottom',
                    top: targetTop + targetHeight,
                    left: targetLeft - (popoverWidth - targetWidth) / 2,
                },
                left: {
                    name: 'left',
                    top: targetTop - (popoverHeight - targetHeight) / 2,
                    left: targetLeft - popoverWidth,
                },
            };
        }

        /**
         * Check if the element is in the viewport.
         * @private
         * @static
         * @param {HTMLElement} element
         * @returns {Boolean} True if the element currently fits inside
         *                    the viewport, false otherwise.
         */
        static _isInViewport(element) {
            const rect = element.getBoundingClientRect();
            const html = document.documentElement;
            return (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || html.clientHeight) &&
                rect.right <= (window.innerWidth || html.clientWidth)
            );
        }

        /**
         * Hide any displayed popover, display the popover in argument and mark
         * it as the one being displayed in the class attribute. Add an event
         * listener on the document to detect any click outside the popover as a
         * closing event.
         * Note that the event listener is added for the capture phase, meaning
         * that it will *always* run before the click listener set on a popover
         * template. This means that there can be no race condition regarding
         * clicking on another popover trigger: any existing popover will be
         * removed during the capture phase, then a new listener will be added
         * in the bubbling phase of the new popover's trigger click event.
         * @static
         * @param {Popover} popover The popover component to display.
         */
        static display(popover) {
            // this should never happen because of the way the events are handled,
            // but in case an imaginative dev puts a popover inside another one, i'd
            // prefer the first one to be hidden anyway, causing the second one to
            // never display itself (since its target won't be in the viewport)
            if (this.displayed) {
                this.displayed._close();
            }
            if (!this.isListening) {
                document.addEventListener('click', documentClickHandler, {
                    capture: true,
                });
                document.addEventListener('scroll', documentScrollHandler, {
                    capture: true,
                });
                window.addEventListener('resize', windowResizeHandler);
                this.isListening = true;
            }
            this.displayed = popover;
            popover.state.displayed = true;
        }

        /**
         * Hide any displayed popover and remove event listeners if no popover is
         * about to replace the current one.
         * @static
         * @param {Boolean} nextPopover: whether a new popover is about to be opened; if true,
         * the document click listener will not be removed.
         */
        static hide(nextPopover) {
            const popover = this.displayed;
            // only remove the listener if we are not about to open a new popover
            if (this.isListening && !nextPopover) {
                document.removeEventListener('click', documentClickHandler, {
                    capture: true,
                });
                document.removeEventListener('scroll', documentScrollHandler, {
                    capture: true,
                });
                window.removeEventListener('resize', windowResizeHandler);
                this.isListening = false;
            }
            popover.state.displayed = false;
            this.displayed = null;
        }
    }

    /**
     * Global handler added on the document for when a popover is currently displayed.
     * A click outside the popover will dismiss the current popover.
     * @param {MouseEvent} e
     */
    const documentClickHandler = function (e) {
        const popover = Popover.displayed.popoverRef;
        if (!popover.el.contains(e.target)) {
            const nextPopover = !!e.target.closest('*[data-popover]');
            Popover.hide(nextPopover);
        }
    };

    /**
     * Reposition the currently displayed popover relative to its traget.
     * @param {Event} e
     */
    const _reposition = function (e) {
        const popover = Popover.displayed;
        popover.show();
    };

    /**
     * Global handler added on the document for when a popover is currently displayed.
     * A scroll event will need to 'reposition' the popover close to its target.
     */
    const documentScrollHandler = _.throttle(_reposition, 50);

    /**
     * Global handler added on the document for when a popover is currently displayed.
     * A resize event will need to 'reposition' the popover close to its target.
     */
    const windowResizeHandler = _.debounce(_reposition, 250);

    Popover.displayed = null;
    Popover.isListening = false;
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

    return Popover;
});
