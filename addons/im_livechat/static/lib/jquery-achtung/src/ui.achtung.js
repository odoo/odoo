/**
 * achtung %%VERSION%%
 *
 * Growl-like notifications for jQuery
 *
 * Copyright (c) 2009 Josh Varner <josh@voxwerk.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * @license http://www.opensource.org/licenses/mit-license.php
 * @author Josh Varner <josh@voxwerk.com>
 */

/*jslint browser:true, white:false, onevar:false, nomen:false, bitwise:false, plusplus:false, immed: false */
/*globals window, jQuery */
(function ($) {

var widgetName = 'achtung';

/**
 * This is based on the jQuery UI $.widget code. I would have just made this
 * a $.widget but I didn't want the jQuery UI dependency.
 */
$.fn.achtung = function (options) {
	var isMethodCall = (typeof options === 'string'),
		args = Array.prototype.slice.call(arguments, isMethodCall ? 1 : 0);

	// handle initialization and non-getter methods
	return this.each(function () {
		// prevent calls to internal methods
		if (isMethodCall && options.substring(0, 1) === '_') {
			return;
		}

		var instance = $.data(this, widgetName);

		// constructor
		if (!instance && !isMethodCall) {
			$.data(this, widgetName, new $.achtung(this))._init(args);
		}

		if (!!instance && isMethodCall && $.isFunction(instance[options])) {
			instance[options].apply(instance, args);
		}
	});
};

$.achtung = function (element) {
    if (!element || !element.nodeType) {
        var el = $('<div>');
        return el.achtung.apply(el, arguments);
    }

    this.container = $(element);
};


/**
 * Static members
 **/
$.extend($.achtung, {
    version: '%%VERSION%%',
    overlay: false,
    wrapper: false,
    defaults: {
        timeout: 10,
        disableClose: false,
        icon: false,
        className: 'achtung-default',
        crossFadeMessage: 500, // 0 to disable
        animateClassSwitch: 0, // 0 to disable (doesn't work with gradient backgrounds)
        showEffects: {'opacity':'toggle'}, // ,'height':'toggle'},
        hideEffects: {'opacity':'toggle'}, // ,'height':'toggle'},
        showEffectDuration: 300,
        hideEffectDuration: 500
    }
});

/**
 * Non-static members
 **/
$.extend($.achtung.prototype, {
    container: false,
    icon: false,
    message: false,
    closeTimer: false,
    options: {},

    _init: function (args) {
        var o, self = this;

        o = this.options = $.extend.apply($, [{}, $.achtung.defaults].concat(args));

        if ((o.animateClassSwitch > 0) && !('switchClass' in $.fn)) {
            o.animateClassSwitch = this.options.animateClassSwitch = 0;
        }

        if (!o.disableClose) {
            $('<span class="achtung-close-button ui-icon ui-icon-close" />')
                .prependTo(this.container)
                .bind({
                    click: function () { self.close(); }
                });
        }

        this.changeIcon(o.icon, true);

        if (o.message) {
            this.message = $('<span>', {
                'class': 'achtung-message',
                html: o.message
            }).appendTo(this.container);
        }

        if ('className' in o) {
            this.container.addClass(o.className);
        }

        if ('css' in o) {
            this.container.css(o.css);
        }

        if (!$.achtung.overlay) {
            $.achtung.overlay = $('<div id="achtung-overlay"><div id="achtung-wrapper"></div></div>');
            $.achtung.overlay.appendTo(document.body);
            $.achtung.wrapper = $('#achtung-wrapper');
        }

        this.container.addClass('achtung').hide().appendTo($.achtung.wrapper);

        if (o.showEffects) {
            this.container.animate(o.showEffects, o.showEffectDuration);
        } else {
            this.container.show();
        }

        this.timeout(o.timeout);
    },

    timeout: function (timeout) {
        var self = this;

        if (this.closeTimer) {
            clearTimeout(this.closeTimer);
        }

        if (timeout > 0) {
            this.closeTimer = setTimeout(function () { self.close(); }, timeout * 1000);
            this.options.timeout = timeout;
        } else if (timeout < 0) {
            this.close();
        }
    },

    /**
     * Change the CSS class associated with this message.
     *
     * @param newClass string Name of new class to associate
     */
    changeClass: function (newClass) {
        var oldClass = '' + this.options.className,
            self = this;

        if (oldClass === newClass) {
            return;
        }

        this.container.queue(function (next) {
            if (self.options.animateClassSwitch > 0) {
                $(this).switchClass(oldClass, newClass, self.options.animateClassSwitch);
            } else {
                $(this).removeClass(oldClass).addClass(newClass);
            }
            next();
        });

        this.options.className = newClass;
    },

    changeIcon: function (newIcon, force) {
        if (!force && this.options.icon === newIcon) {
            return;
        }

        if (!!this.icon) {
            if (newIcon) {
                this.icon.removeClass(this.options.icon).addClass(newIcon);
            } else {
                this.icon.remove();
                this.icon = false;
            }
        } else if (newIcon) {
            this.icon = $('<span class="achtung-message-icon ui-icon ' + newIcon + '" />');
            this.container.prepend(this.icon);
        }

        this.options.icon = newIcon;
    },

    changeMessage: function (newMessage) {
        if (this.options.crossFadeMessage > 0) {
            this.message.clone()
                .css('position', 'absolute')
                .insertBefore(this.message)
                .fadeOut(this.options.crossFadeMessage, function () { $(this).remove(); });

            this.message.hide().html(newMessage).fadeIn(this.options.crossFadeMessage);
        } else {
            this.message.html(newMessage);
        }

        this.options.message = newMessage;
    },

    update: function () {
        var options = $.extend.apply($, [{}].concat(Array.prototype.slice.call(arguments, 0))),
            map = {
                className: 'changeClass',
                css: 'css',
                icon: 'changeIcon',
                message: 'changeMessage',
                timeout: 'timeout'
            };

        for (var prop in map) {
            if (prop in options) {
                this[map[prop]](options[prop]);
            }
        }
    },

    isVisible: function () {
        return (true === this.container.is(':visible'));
    },

    _trigger: function (type, data) {
        this.container.trigger(widgetName + type, data);
    },

    close: function () {
        var o = this.options, self = this;

        this._trigger('close');

        if (o.hideEffects) {
            this.container.animate(o.hideEffects, o.hideEffectDuration, function () {
                self.remove();
            });
        } else {
            this.container.hide();
            this.remove();
        }
    },

    remove: function () {
        this.container.remove();

        if ($.achtung.wrapper && !($.achtung.wrapper.contents().length)) {
            $.achtung.wrapper = false;
            $.achtung.overlay.remove();
            $.achtung.overlay = false;
        }
    }
});

})(jQuery);