/**
    This code has been more that widely inspired by easyZoom library.

    Copyright 2013 Matt Hinchliffe

    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.
**/

/** @type {WeakMap<HTMLElement, ZoomOdoo>} */
const instanceMap = new WeakMap();

const noop = () => {};

const defaults = {
    // Attribute to retrieve the zoom image URL from.
    linkTag: 'a',
    linkAttribute: 'data-zoom-image',

    // event to trigger zoom
    event: 'click', //or mouseenter

    // Timer before trigger zoom
    timer: 0,

    // Prevent clicks on the zoom image link.
    preventClicks: true,

    // disable on mobile
    disabledOnMobile: true,

    // Callback function to execute before the flyout is displayed.
    beforeShow: noop,

    // Callback function to execute before the flyout is removed.
    beforeHide: noop,

    // Callback function to execute when the flyout is displayed.
    onShow: noop,

    // Callback function to execute when the flyout is removed.
    onHide: noop,

    // Callback function to execute when the cursor is moved while over the image.
    onMove: noop,

    // Callback function to execute when the flyout is attached to the target.
    beforeAttach: noop,
};

/**
 * ZoomOdoo — vanilla JS image zoom widget.
 * @param {HTMLElement} target
 * @param {Object} [options]
 */
function ZoomOdoo(target, options) {
    this.target = target;
    this.opts = Object.assign({}, defaults, options, target.dataset);

    // AbortController for grouped event cleanup
    this._ac = new AbortController();

    // Module-level state for move calculations
    this._dw = 0;
    this._dh = 0;
    this._rw = 0;
    this._rh = 0;
    this._lx = 0;
    this._ly = 0;

    if (this.isOpen === undefined) {
        this._init();
    }
}

/**
 * Init
 * @private
 */
ZoomOdoo.prototype._init = function () {
    if (window.outerWidth > 467 || !this.opts.disabledOnMobile) {
        const linkEl = this.target.querySelector(this.opts.linkTag);
        this.link = linkEl || this.target;
        const imgEl = this.target.querySelector('img');
        this.image = imgEl || this.target;

        this.flyout = document.createElement('div');
        this.flyout.className = 'zoomodoo-flyout';

        let attach = this.target;
        if (this.opts.attach !== undefined) {
            const closest = this.target.closest(this.opts.attach);
            if (closest) {
                attach = closest;
            }
        }
        this._attachParent = attach.parentNode;

        const signal = this._ac.signal;
        this._attachParent.addEventListener('mousemove', this._onMove.bind(this), { signal });
        this._attachParent.addEventListener('touchmove', this._onMove.bind(this), { signal });
        this._attachParent.addEventListener('mouseleave', this._onLeave.bind(this), { signal });
        this._attachParent.addEventListener('touchend', this._onLeave.bind(this), { signal });
        this.target.addEventListener(this.opts.event, this._onEnter.bind(this), { signal });
        this.target.addEventListener('touchstart', this._onEnter.bind(this), { signal });

        if (this.opts.preventClicks) {
            this.target.addEventListener('click', (e) => e.preventDefault(), { signal });
        } else {
            this.target.addEventListener('click', () => {
                this.hide();
                this._ac.abort();
            }, { signal });
        }
    }
};

/**
 * Show
 * @param {MouseEvent|TouchEvent} e
 * @param {boolean} [testMouseOver]
 */
ZoomOdoo.prototype.show = function (e, testMouseOver) {
    if (this.opts.beforeShow.call(this) === false) return;

    if (!this.isReady) {
        return this._loadImage(this.link.getAttribute(this.opts.linkAttribute), () => {
            if (this.isMouseOver || !testMouseOver) {
                this.show(e);
            }
        });
    }

    let attach = this.target;
    if (this.opts.attach !== undefined) {
        const closest = this.target.closest(this.opts.attach);
        if (closest) {
            attach = closest;
        }
    }

    // Prevents having multiple zoom flyouts
    const existing = attach.parentNode.querySelector('.zoomodoo-flyout');
    if (existing) existing.remove();
    this.flyout.removeAttribute('style');
    attach.parentNode.append(this.flyout);

    if (this.opts.attachToTarget) {
        this.opts.beforeAttach.call(this);

        // Be sure that the flyout is at top 0, left 0 to ensure correct computation
        this.flyout.style.position = 'fixed';
        const flyoutRect = this.flyout.getBoundingClientRect();
        if (flyoutRect.left > 0) {
            const flyoutLeft = parseFloat(getComputedStyle(this.flyout).left) || 0;
            this.flyout.style.left = (flyoutLeft - flyoutRect.left) + 'px';
        }
        if (flyoutRect.top > 0) {
            const flyoutTop = parseFloat(getComputedStyle(this.flyout).top) || 0;
            this.flyout.style.top = (flyoutTop - flyoutRect.top) + 'px';
        }

        if (this.zoom.offsetHeight < this.flyout.offsetHeight) {
            this.flyout.style.height = this.zoom.offsetHeight + 'px';
        }
        if (this.zoom.offsetWidth < this.flyout.offsetWidth) {
            this.flyout.style.width = this.zoom.offsetWidth + 'px';
        }

        const targetRect = this.target.getBoundingClientRect();
        const scrollX = window.scrollX;
        const scrollY = window.scrollY;
        const offsetLeft = targetRect.left + scrollX;
        const offsetTop = targetRect.top + scrollY;
        let left = offsetLeft - this.flyout.offsetWidth;
        let top = offsetTop;

        const docWidth = document.documentElement.clientWidth;
        const docHeight = document.documentElement.clientHeight;

        // Position the zoom on the right side of the target
        // if there's not enough room on the left
        if (left < 0) {
            if (offsetLeft < (docWidth / 2)) {
                left = offsetLeft + this.target.offsetWidth;
            } else {
                left = 0;
            }
        }

        // Prevents the flyout to overflow
        if (left + this.flyout.offsetWidth > docWidth) {
            this.flyout.style.width = (docWidth - left) + 'px';
        } else if (left === 0) {
            this.flyout.style.width = offsetLeft + 'px';
        }

        // Prevents the zoom to be displayed outside the current viewport
        if ((top + this.flyout.offsetHeight) > docHeight) {
            top = docHeight - this.flyout.offsetHeight;
        }

        this.flyout.style.transform = `translate3d(${left}px, ${top}px, 0px)`;
    } else {
        // Computing flyout max-width depending to the available space on the right
        const rightAvailableSpace = document.body.clientWidth - this.flyout.getBoundingClientRect().left;
        this.flyout.style.maxWidth = rightAvailableSpace + 'px';
    }

    const w1 = this.target.offsetWidth;
    const h1 = this.target.offsetHeight;
    const w2 = this.flyout.offsetWidth;
    const h2 = this.flyout.offsetHeight;

    this._dw = Math.max(this.zoom.offsetWidth - w2, 0);
    this._dh = Math.max(this.zoom.offsetHeight - h2, 0);

    this._rw = this._dw / w1;
    this._rh = this._dh / h1;

    this.isOpen = true;
    this.opts.onShow.call(this);

    if (e) {
        this._move(e);
    }
};

/**
 * On enter
 * @private
 * @param {Event} e
 */
ZoomOdoo.prototype._onEnter = function (e) {
    const touches = e.touches;
    e.preventDefault();
    this.isMouseOver = true;

    setTimeout(() => {
        if (this.isMouseOver && (!touches || touches.length === 1)) {
            this.show(e, true);
        }
    }, this.opts.timer);
};

/**
 * On move
 * @private
 * @param {Event} e
 */
ZoomOdoo.prototype._onMove = function (e) {
    if (!this.isOpen) return;
    e.preventDefault();
    this._move(e);
};

/**
 * On leave
 * @private
 */
ZoomOdoo.prototype._onLeave = function () {
    this.isMouseOver = false;
    if (this.isOpen) {
        this.hide();
    }
};

/**
 * On load
 * @private
 * @param {Function} callback
 * @param {Event} e
 */
ZoomOdoo.prototype._onLoad = function (callback, e) {
    if (!e.currentTarget.width) return;
    this.isReady = true;
    this.flyout.innerHTML = '';
    this.flyout.append(this.zoom);
    if (callback) {
        callback();
    }
};

/**
 * Load image
 * @private
 * @param {string} href
 * @param {Function} callback
 */
ZoomOdoo.prototype._loadImage = function (href, callback) {
    const zoom = new Image();
    this.zoom = zoom;
    zoom.addEventListener('load', this._onLoad.bind(this, callback));
    zoom.style.position = 'absolute';
    zoom.src = href;
};

/**
 * Move
 * @private
 * @param {Event} e
 */
ZoomOdoo.prototype._move = function (e) {
    if (e.type.indexOf('touch') === 0) {
        const touchlist = e.touches;
        this._lx = touchlist[0].pageX;
        this._ly = touchlist[0].pageY;
    } else {
        this._lx = e.pageX || this._lx;
        this._ly = e.pageY || this._ly;
    }

    const targetRect = this.target.getBoundingClientRect();
    const offsetTop = targetRect.top + window.scrollY;
    const offsetLeft = targetRect.left + window.scrollX;
    const pt = this._ly - offsetTop;
    const pl = this._lx - offsetLeft;
    const xt = Math.ceil(pt * this._rh);
    const xl = Math.ceil(pl * this._rw);

    // Close if outside
    if (!this.opts.attachToTarget && (xl < 0 || xt < 0 || xl > this._dw || xt > this._dh || this._lx > (offsetLeft + this.target.offsetWidth))) {
        this.hide();
    } else {
        const top = xt * -1;
        const left = xl * -1;

        this.zoom.style.top = top + 'px';
        this.zoom.style.left = left + 'px';

        this.opts.onMove.call(this, top, left);
    }
};

/**
 * Hide
 */
ZoomOdoo.prototype.hide = function () {
    if (!this.isOpen) return;
    if (this.opts.beforeHide.call(this) === false) return;

    this.flyout.remove();
    this.isOpen = false;

    this.opts.onHide.call(this);
};

/**
 * Initialize zoom on an element. Replaces the old jQuery plugin API.
 * @param {HTMLElement} el
 * @param {Object} [options]
 * @returns {ZoomOdoo}
 */
export function initZoomOdoo(el, options) {
    let api = instanceMap.get(el);
    if (!api) {
        api = new ZoomOdoo(el, options);
        instanceMap.set(el, api);
    } else if (api.isOpen === undefined) {
        api._init();
    }
    return api;
}
