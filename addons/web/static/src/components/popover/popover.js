/** @odoo-module **/

import { debounce, throttle } from "../../utils/timing";

const { Component, QWeb } = owl;
const { Portal } = owl.misc;
const { useRef, useState } = owl.hooks;

export class Popover extends Component {
  setup() {
    this.state = useState({
      displayed: false,
    });

    this._hasExternalListeners = false;
    this._onClick = this.onClick.bind(this);
    this._onMouseEnter = this.onMouseEnter.bind(this);
    this._onMouseLeave = this.onMouseLeave.bind(this);
    this._onDocumentClick = this.onClickAway.bind(this);
    this._onWindowScroll = throttle(this._compute.bind(this), 50);
    this._onWindowResize = debounce(this._compute.bind(this), 250);

    this._targetObserver = new MutationObserver(this.onTargetMutate.bind(this));
    this._isTargetObserved = false;

    this.popoverRef = useRef("popover");
  }

  mounted() {
    this._compute();
    this._addTargetListeners();
  }
  patched() {
    this._compute();
  }
  willUnmount() {
    this._disconnectTargetObserver();
    this._removeTargetListeners();
    this._removeExternalListeners();
  }

  //----------------------------------------------------------------------------
  // Getters
  //----------------------------------------------------------------------------

  /**
   * @returns {boolean}
   */
  get isDisplayed() {
    return this.props.trigger === "none" || this.state.displayed;
  }
  /**
   * @returns {HTMLElement}
   */
  get target() {
    return this.props.target ? document.querySelector(this.props.target) : this.el;
  }

  //----------------------------------------------------------------------------
  // Private
  //----------------------------------------------------------------------------

  /**
   * @private
   */
  _addExternalListeners() {
    if (!this._hasExternalListeners) {
      document.addEventListener("click", this._onDocumentClick);
      document.addEventListener("scroll", this._onWindowScroll);
      window.addEventListener("resize", this._onWindowResize);
      this._hasExternalListeners = true;
    }
  }
  /**
   * @private
   */
  _addTargetListeners() {
    const target = this.target;
    if (target) {
      target.addEventListener("click", this._onClick);
      target.addEventListener("mouseenter", this._onMouseEnter);
      target.addEventListener("mouseleave", this._onMouseLeave);
    }
  }
  /**
   * Computes the popover according to its props. This method will try to
   * position the popover as requested (according to the `position` props).
   * If the requested position does not fit the viewport, other positions will
   * be tried in a clockwise order starting a the requested position
   * (e.g. starting from left: top, right, bottom). If no position is found
   * that fits the viewport, "bottom" is used.
   *
   * @private
   */
  _compute() {
    const target = this.target;
    if (!target) {
      return;
    }

    if (!this.isDisplayed) {
      this._removeExternalListeners();
      this._disconnectTargetObserver();
      return;
    }
    this._connectTargetObserver();
    this._addExternalListeners();

    const positioningData = this.constructor.computePositioningData(this.popoverRef.el, target);

    const ORDERED_POSITIONS = ["top", "bottom", "left", "right"];
    // copy the default ordered position to avoid updating them in place
    const positionIndex = ORDERED_POSITIONS.indexOf(this.props.position);
    // check if the requested position fits the viewport; if not,
    // try all other positions and find one that does
    const position = ORDERED_POSITIONS.slice(positionIndex)
      .concat(ORDERED_POSITIONS.slice(0, positionIndex))
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
    for (const pos of ORDERED_POSITIONS) {
      this.popoverRef.el.classList.remove(`o_popover_${pos}`);
    }

    if (position) {
      // apply the preferred found position that fits the viewport
      this.popoverRef.el.classList.add(`o_popover_${position.name}`);
    } else {
      // use the given `position` props because no position fits
      this.popoverRef.el.style.top = `${positioningData[this.props.position].top}px`;
      this.popoverRef.el.style.left = `${positioningData[this.props.position].left}px`;
      this.popoverRef.el.classList.add(`o_popover_${this.props.position}`);
    }
  }
  /**
   * @private
   */
  _connectTargetObserver() {
    if (!this._isTargetObserved) {
      this._isTargetObserved = true;
      this._targetObserver.observe(this.target.parentElement, { childList: true });
    }
  }
  /**
   * @private
   */
  _disconnectTargetObserver() {
    if (this._isTargetObserved) {
      this._isTargetObserved = false;
      this._targetObserver.disconnect();
    }
  }
  /**
   * @private
   */
  _removeExternalListeners() {
    if (this._hasExternalListeners) {
      document.removeEventListener("click", this._onDocumentClick);
      document.removeEventListener("scroll", this._onWindowScroll);
      window.removeEventListener("resize", this._onWindowResize);
      this._hasExternalListeners = false;
    }
  }
  /**
   * @private
   */
  _removeTargetListeners() {
    const target = this.target;
    if (target) {
      target.removeEventListener("click", this._onClick);
      target.removeEventListener("mouseenter", this._onMouseEnter);
      target.removeEventListener("mouseleave", this._onMouseLeave);
    }
  }

  //----------------------------------------------------------------------------
  // Handlers
  //----------------------------------------------------------------------------

  /**
   * Popover must recompute its position when children content changes.
   */
  onCompute() {
    this._compute();
  }
  /**
   * Toggles the popover depending on its current state.
   */
  onClick() {
    if (this.props.trigger === "click") {
      this.state.displayed = !this.state.displayed;
    }
  }
  /**
   * A click outside the popover will dismiss the current popover.
   */
  onClickAway(ev) {
    // Handled by `_onClick`.
    if (this.target.contains(ev.target)) {
      return;
    }

    // Ignore click inside the popover.
    if (this.popoverRef.el && this.popoverRef.el.contains(ev.target)) {
      return;
    }

    if (this.props.closeOnClickAway) {
      this.trigger("popover-closed");
    }
  }
  /**
   * Closes the popover
   */
  onClose() {
    this.state.displayed = false;
  }
  /**
   * Opens the popover when it's hovered.
   */
  onMouseEnter() {
    if (this.props.trigger === "hover") {
      this.state.displayed = true;
    }
  }
  /**
   * Closes the popover when the cursor moves away.
   */
  onMouseLeave() {
    if (this.props.trigger === "hover") {
      this.state.displayed = false;
    }
  }
  /**
   * Closes the popover when the target is removed from dom.
   */
  onTargetMutate() {
    const target = this.target;
    if (!target) {
      this._disconnectTargetObserver();
      this.trigger("popover-closed");
    } else {
      for (const mutation of mutations) {
        for (const node of mutation.removedNodes) {
          if (node === target) {
            this._disconnectTargetObserver();
            this.trigger("popover-closed");
            break;
          }
        }
      }
    }
  }
}

Popover.components = {
  Portal,
};
Popover.template = "web.PopoverWowl";
Popover.defaultProps = {
  closeOnClickAway: true,
  position: "bottom",
  trigger: "click",
};
Popover.props = {
  closeOnClickAway: Boolean,
  popoverClass: {
    optional: true,
    type: String,
  },
  position: {
    type: String,
    validate: (p) => ["top", "bottom", "left", "right"].includes(p),
  },
  target: {
    optional: true,
    type: String,
  },
  trigger: {
    type: String,
    validate: (t) => ["click", "hover", "none"].includes(t),
  },
};

/**
 * Compute the expected positioning coordinates for each possible
 * positioning based on the target and popover sizes.
 * In particular the popover must not overflow the viewport in any
 * direction, it should actually stay at `margin` distance from the
 * border to look good.
 *
 * @param {HTMLElement} popoverElement The popover element
 * @param {HTMLElement} targetElement The target element, to which
 *  the popover will be visually "bound"
 * @param {integer} [margin=16] Minimal accepted margin from the border
 *  of the viewport.
 * @returns {Object}
 */
Popover.computePositioningData = function (popoverElement, targetElement, margin = 16) {
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
      windowWidth - popoverWidth - margin
    )
  );
  const topOffsetForHorizontal = Math.max(
    margin,
    Math.min(
      Math.round(targetTop - (popoverHeight - targetHeight) / 2),
      windowHeight - popoverHeight - margin
    )
  );
  return {
    top: {
      name: "top",
      top: Math.round(targetTop - popoverHeight),
      left: leftOffsetForVertical,
    },
    right: {
      name: "right",
      top: topOffsetForHorizontal,
      left: Math.round(targetLeft + targetWidth),
    },
    bottom: {
      name: "bottom",
      top: Math.round(targetTop + targetHeight),
      left: leftOffsetForVertical,
    },
    left: {
      name: "left",
      top: topOffsetForHorizontal,
      left: Math.round(targetLeft - popoverWidth),
    },
  };
};

/** @todo remove this when wowl = web */
delete QWeb.components.Popover;
QWeb.registerComponent("Popover", Popover);
