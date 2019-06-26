odoo.define('web.zoomodoo', function (require) {
'use strict';

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

    // Prevent clicks on the zoom image link.
    preventClicks: true,

    // disable on mobile
    disabledOnMobile: true,

    // Callback function to execute before the flyout is displayed.
    beforeShow: $.noop,

    // Callback function to execute before the flyout is removed.
    beforeHide: $.noop,

    // Callback function to execute when the flyout is displayed.
    onShow: $.noop,

    // Callback function to execute when the flyout is removed.
    onHide: $.noop,

    // Callback function to execute when the cursor is moved while over the image.
    onMove: $.noop,

    // Callback function to execute when the flyout is attached to the target.
    beforeAttach: $.noop

};

/**
 * ZoomOdoo
 * @constructor
 * @param {Object} target
 * @param {Object} options (Optional)
 */
function ZoomOdoo(target, options) {
    this.$target = $(target);
    this.opts = $.extend({}, defaults, options, this.$target.data());

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
        this.$link  = this.$target.find(this.opts.linkTag).length && this.$target.find(this.opts.linkTag) || this.$target;
        this.$image  = this.$target.find('img').length && this.$target.find('img') || this.$target;
        this.$flyout = $('<div class="zoomodoo-flyout" />');

        var $attach = this.$target;
        if (this.opts.attach !== undefined && this.$target.parents(this.opts.attach).length) {
            $attach = this.$target.parents(this.opts.attach);
        }
        $attach.parent().on('mousemove.zoomodoo touchmove.zoomodoo', $.proxy(this._onMove, this));
        $attach.parent().on('mouseleave.zoomodoo touchend.zoomodoo', $.proxy(this._onLeave, this));
        this.$target.on(this.opts.event + '.zoomodoo touchstart.zoomodoo', $.proxy(this._onEnter, this));

        if (this.opts.preventClicks) {
            this.$target.on('click.zoomodoo', function (e) { e.preventDefault(); });
        } else {
            var self = this;
            this.$target.on('click.zoomodoo', function () { self.hide(); self.$target.unbind(); });
        }
    }
};

/**
 * Show
 * @param {MouseEvent|TouchEvent} e
 * @param {Boolean} testMouseOver (Optional)
 */
ZoomOdoo.prototype.show = function (e, testMouseOver) {
    var w1, h1, w2, h2;
    var self = this;

    if (this.opts.beforeShow.call(this) === false) return;

    if (!this.isReady) {
        return this._loadImage(this.$link.attr(this.opts.linkAttribute), function () {
            if (self.isMouseOver || !testMouseOver) {
                self.show(e);
            }
        });
    }

    var $attach = this.$target;
    if (this.opts.attach !== undefined && this.$target.parents(this.opts.attach).length) {
        $attach = this.$target.parents(this.opts.attach);
    }

    // Prevents having multiple zoom flyouts
    $attach.parent().find('.zoomodoo-flyout').remove();
    this.$flyout.removeAttr('style');
    $attach.parent().append(this.$flyout);

    if (this.opts.attachToTarget) {
        this.opts.beforeAttach.call(this);

        if(this.$zoom.height() < this.$flyout.height()) {
             this.$flyout.css('height', this.$zoom.height() + 'px');
        }
        if(this.$zoom.width() < this.$flyout.width()) {
             this.$flyout.css('width', this.$zoom.width() + 'px');
        }

        var offset = this.$target.offset();
        var left = offset.left - this.$flyout.width();
        var top = offset.top;

        // Position the zoom on the right side of the target
        // if there's not enough room on the left
        if(left < 0) {
            if(offset.left < ($(document).width() / 2)) {
                left = offset.left + this.$target.width();
            } else {
                left = 0;
            }
        }

        // Prevents the flyout to overflow 
        if(left + this.$flyout.width() > $(document).width()) {
            this.$flyout.css('width',  $(document).width() - left + 'px');
        } else if(left === 0) { // Limit the max width if displayed on the left
            this.$flyout.css('width', offset.left + 'px');
        }

        // Prevents the zoom to be displayed outside the current viewport
        if((top + this.$flyout.height()) > $(document).height()) {
            top = $(document).height() - this.$flyout.height();
        }

        this.$flyout.css('transform', 'translate3d(' + left + 'px, ' + top + 'px, 0px)');
    }

    w1 = this.$target.width();
    h1 = this.$target.height();

    w2 = this.$flyout.width();
    h2 = this.$flyout.height();

    dw = this.$zoom.width() - w2;
    dh = this.$zoom.height() - h2;

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
    var touches = e.originalEvent.touches;

    this.isMouseOver = true;
    if (!touches || touches.length === 1) {
        e.preventDefault();
        this.show(e, true);
    }
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

    this.$flyout.html(this.$zoom);

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
    var zoom = new Image();

    this.$zoom = $(zoom).on('load', callback, $.proxy(this._onLoad, this));

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
        var touchlist = e.touches || e.originalEvent.touches;
        lx = touchlist[0].pageX;
        ly = touchlist[0].pageY;
    } else {
        lx = e.pageX || lx;
        ly = e.pageY || ly;
    }

    var offset  = this.$target.offset();
    var pt = ly - offset.top;
    var pl = lx - offset.left;
    var xt = Math.ceil(pt * rh);
    var xl = Math.ceil(pl * rw);

    // Close if outside
    if (xl < 0 || xt < 0 || xl > dw || xt > dh || lx > (offset.left + this.$target.width())) {
        this.hide();
    } else {
        var top = xt * -1;
        var left = xl * -1;

        this.$zoom.css({
            top: top,
            left: left
        });

        this.opts.onMove.call(this, top, left);
    }

};

/**
 * Hide
 */
ZoomOdoo.prototype.hide = function () {
    if (!this.isOpen) return;
    if (this.opts.beforeHide.call(this) === false) return;

    this.$flyout.detach();
    this.isOpen = false;

    this.opts.onHide.call(this);
};

// jQuery plugin wrapper
$.fn.zoomOdoo = function (options) {
    return this.each(function () {
        var api = $.data(this, 'zoomOdoo');

        if (!api) {
            $.data(this, 'zoomOdoo', new ZoomOdoo(this, options));
        } else if (api.isOpen === undefined) {
            api._init();
        }
    });
};
});
