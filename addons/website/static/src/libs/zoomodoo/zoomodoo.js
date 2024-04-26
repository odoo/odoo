/** @odoo-module **/

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

var dw, dh, rw, rh, lx, ly;

var defaults = {

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
    beforeShow: function() {},

    // Callback function to execute before the flyout is removed.
    beforeHide: function() {},

    // Callback function to execute when the flyout is displayed.
    onShow: function() {},

    // Callback function to execute when the flyout is removed.
    onHide: function() {},

    // Callback function to execute when the cursor is moved while over the image.
    onMove: function() {},

    // Callback function to execute when the flyout is attached to the target.
    beforeAttach: function() {}

};

/**
 * ZoomOdoo
 * @constructor
 * @param {Object} target
 * @param {Object} options (Optional)
 */
function ZoomOdoo(target, options) {
    this.opts = Object.assign({}, defaults, options, target.dataset);

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
        const targetLinks = target.querySelectorAll(this.opts.linkTag);
        this.link = targetLinks.length > 0 ? targetLinks : target;
        this.image  = target.querySelectorAll('img').length && target.querySelectorAll('img') || target;
        this.flyout = document.createElement('div');
        this.flyout.className = 'zoomodoo-flyout';

        let attach = target;
        if (this.opts.attach !== undefined && target.closest(this.opts.attach).length) {
            attach = target.closest(this.opts.attach);
        }
        const parentElement = attach.parentElement;
        parentElement.addEventListener('mousemove', this._onMove.bind(this));
        parentElement.addEventListener('touchmove', this._onMove.bind(this));
        target.addEventListener(this.opts.event + '.zoomodoo', this._onEnter.bind(this));
        target.addEventListener('touchstart.zoomodoo', this._onEnter.bind(this));

        if (this.opts.preventClicks) {
            target.addEventListener('click', function (e) { e.preventDefault(); });
        } else {
            let self = this;
            target.addEventListener('click', function () { self.hide(); self.target.removeEventListener('click', arguments.callee); });
        }
    }
};

/**
 * Show
 * @param {MouseEvent|TouchEvent} e
 * @param {Boolean} testMouseOver (Optional)
 */
ZoomOdoo.prototype.show = function (e, testMouseOver) {
    let w1, h1, w2, h2;
    const self = this;

    if (this.opts.beforeShow.call(this) === false) return;

    if (!this.isReady) {
        return this._loadImage(this.link.getAttribute(this.opts.linkAttribute), function () {
            if (self.isMouseOver || !testMouseOver) {
                self.show(e);
            }
        });
    }

    let attach = target;
    if (this.opts.attach !== undefined && target.closest(this.opts.attach).length) {
        attach = target.closest(this.opts.attach);
    }

    const attachParent = attach.parentElement;
    // Prevents having multiple zoom flyouts
    attachParent.querySelectorAll('.zoomodoo-flyout').forEach(function (flyout) {
        flyout.remove();
    });
    this.flyout.removeAttribute('style');
    attachParent.append(this.flyout);

    if (this.opts.attachToTarget) {
        this.opts.beforeAttach.call(this);

        // Be sure that the flyout is at top 0, left 0 to ensure correct computation
        // e.g. employees kanban on dashboard
        this.flyout.style.position = 'fixed';
        const flyoutOffset = this.flyout.getBoundingClientRect();
        if (flyoutOffset.left > 0) {
            const flyoutLeft = parseFloat(flyoutOffset.left.replace('px',''));
            this.flyout.style.left = flyoutLeft - flyoutOffset.left + 'px';
        }
        if (flyoutOffset.top > 0) {
            const flyoutTop = parseFloat(flyoutOffset.top.replace('px',''));
            this.flyout.style.top = flyoutTop - flyoutOffset.top + 'px';
        }

        if(this.zoom.style.height < flyoutOffset.height) {
            this.flyout.style.height = this.zoom.style.height + 'px';
        }
        if(this.zoom.style.width < flyoutOffset.width) {
            this.flyout.style.width =this.zoom.style.width + 'px';
        }

        const offset = target.getBoundingClientRect();
        let left = offset.left - flyoutOffset.width;
        let top = offset.top;

        // Position the zoom on the right side of the target
        // if there's not enough room on the left
        if(left < 0) {
            if(offset.left < (document.getBoundingClientRect().width / 2)) {
                left = offset.left + offset.width;
            } else {
                left = 0;
            }
        }

        // Prevents the flyout to overflow
        if(left + flyoutOffset.width > document.getBoundingClientRect().width) {
            this.flyout.style.width = document.getBoundingClientRect().width - left + 'px';
        } else if(left === 0) { // Limit the max width if displayed on the left
            this.flyout.style.width =  offset.left + 'px';
        }

        // Prevents the zoom to be displayed outside the current viewport
        if((top + flyoutOffset.height) >document.getBoundingClientRect().height) {
            top = document.getBoundingClientRect().height -flyoutOffset.height;
        }

        this.flyout.style.transform = 'translate3d(' + left + 'px, ' + top + 'px, 0px)';
    } else {
        // Computing flyout max-width depending to the available space on the right to avoid overflow-x issues
        // e.g. width too high so a right zoomed element is not visible (need to scroll on x axis)
        let rightAvailableSpace = document.body.clientWidth - flyoutOffset.left;
        this.flyout.style.maxWidth = rightAvailableSpace + 'px';
    }

    w1 = target.offsetWidth;
    h1 = target.offsetHeight;

    w2 = this.flyout.style.width;
    h2 =this.flyout.style.height;

    dw = this.zoom.style.width - w2;
    dh = this.zoom.style.height- h2;

    // For the case where the zoom image is actually smaller than
    // the flyout.
    if (dw < 0) dw = 0;
    if (dh < 0) dh = 0;

    rw = dw / w1;
    rh = dh / h1;

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
    const self = this;
    const touches = e.originalEvent.touches;
    e.preventDefault();
    this.isMouseOver = true;

    setTimeout(function () {
        if (self.isMouseOver && (!touches || touches.length === 1)) {
            self.show(e, true);
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
 * @param {Event} e
 */
ZoomOdoo.prototype._onLoad = function (e) {
    // IE may fire a load event even on error so test the image dimensions
    if (!e.currentTarget.width) return;

    this.isReady = true;

    this.flyout.innerHTML = this.zoom.outerHTML;

    if (e.data.call) {
        e.data();
    }
};

/**
 * Load image
 * @private
 * @param {String} href
 * @param {Function} callback
 */
ZoomOdoo.prototype._loadImage = function (href, callback) {
    const zoom = new Image();

    this.zoom = zoom.addEventListener('load', callback, this._onLoad.bind(this));

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
        const touchlist = e.touches || e.originalEvent.touches;
        lx = touchlist[0].pageX;
        ly = touchlist[0].pageY;
    } else {
        lx = e.pageX || lx;
        ly = e.pageY || ly;
    }

    const offset  = target.getBoundingClientRect();
    const pt = ly - offset.top;
    const pl = lx - offset.left;
    const xt = Math.ceil(pt * rh);
    const xl = Math.ceil(pl * rw);

    // Close if outside
    if (!this.opts.attachToTarget && (xl < 0 || xt < 0 || xl > dw || xt > dh || lx > (offset.left + target.style.outerWidth))) {
        this.hide();
    } else {
        let top = xt * -1;
        let left = xl * -1;

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

// jQuery plugin wrapper
window.zoomOdoo = function(options) {
    Array.from(this).forEach(function(element) {
        var api = element.dataset.zoomOdoo;

        if (!api) {
            element.dataset.zoomOdoo = new ZoomOdoo(element, options);
        } else if (api.isOpen === undefined) {
            api._init();
        }
    });
};
