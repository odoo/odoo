/*
* TipTip
* Copyright 2010 Drew Wilson
* www.drewwilson.com
* code.drewwilson.com/entry/tiptip-jquery-plugin
*
* Version 1.3   -   Updated: Mar. 23, 2010
*
* This Plug-In will create a custom tooltip to replace the default
* browser tooltip. It is extremely lightweight and very smart in
* that it detects the edges of the browser window and will make sure
* the tooltip stays within the current window size. As a result the
* tooltip will adjust itself to be displayed above, below, to the left 
* or to the right depending on what is necessary to stay within the
* browser window. It is completely customizable as well via CSS.
*
* This TipTip jQuery plug-in is dual licensed under the MIT and GPL licenses:
*   http://www.opensource.org/licenses/mit-license.php
*   http://www.gnu.org/licenses/gpl.html
*/

(function ($) {
    $.fn.tipTip = function (options) {

        var defaults = {
            activation: 'hover', // How to show (and hide) the tooltip. Can be: hover, focus, click and manual.
            keepAlive: false, // When true the tooltip won't disapper when the mouse moves away from the element. Instead it will be hidden when it leaves the tooltip.
            maxWidth: '200px', // The max-width to set on the tooltip. You may also use the option cssClass to set this.
            edgeOffset: 0, // The offset between the tooltip arrow edge and the element that has the tooltip.
            defaultPosition: 'bottom', // The position of the tooltip. Can be: top, right, bottom and left.
            delay: 400, // The delay in msec to show a tooltip.
            fadeIn: 200, // The length in msec of the fade in.
            fadeOut: 200, // The length in msec of the fade out.
            attribute: 'title', // The attribute to fetch the tooltip text if the option content is false.
            content: false, // HTML or String or Function (that returns HTML or String) to fill TipTIp with
            enter: function () { }, // Callback function before a tooltip is shown.
            afterEnter: function () { }, // Callback function after a tooltip is shown.
            exit: function () { }, // Callback function before a tooltip is hidden.
            afterExit: function () { }, // Callback function after a tooltip is hidden.
            cssClass: '', // CSS class that will be applied on the tooltip before showing only for this instance of tooltip.
            detectTextDir: true // When false auto-detection for right-to-left text will be disable (When true affects a bit the performance).
        };

        // Setup tip tip elements and render them to the DOM
        if ($('#tiptip_holder').length <= 0) {
            var tiptip_inner_arrow = $('<div>', { id: 'tiptip_arrow_inner' }),
                tiptip_arrow = $('<div>', { id: 'tiptip_arrow' }).append(tiptip_inner_arrow),
                tiptip_content = $('<div>', { id: 'tiptip_content' }),
                tiptip_holder = $('<div>', { id: 'tiptip_holder' }).append(tiptip_arrow).append(tiptip_content);
            $('body').append(tiptip_holder);
        } else {
            var tiptip_holder = $('#tiptip_holder'),
                tiptip_content = $('#tiptip_content'),
                tiptip_arrow = $('#tiptip_arrow');
        }

        return this.each(function () {
            var org_elem = $(this),
                data = org_elem.data('tipTip'),
                opts = data && data.options || $.extend({}, defaults, options),
                callback_data = { 
                    holder: tiptip_holder, 
                    content: tiptip_content, 
                    arrow: tiptip_arrow, 
                    options: opts 
                };

            if (data) {
                switch (options) {
                    case 'show':
                        activate();
                        break;
                    case 'hide':
                        deactivate();
                        break;
                    case 'destroy':
                        org_elem.unbind('.tipTip').removeData('tipTip');
                        break;
                    case 'position':
                        position_tiptip();
                }
            } else {
                var timeout = false;

                org_elem.data('tipTip', { options: opts });

                if (opts.activation == 'hover') {
                    org_elem.bind('mouseenter.tipTip', function () {
                        activate();
                    }).bind('mouseleave.tipTip', function () {
                        if (!opts.keepAlive) {
                            deactivate();
                        } else {
                            tiptip_holder.one('mouseleave.tipTip', function () {
                                deactivate();
                            });
                        }
                    });
                } else if (opts.activation == 'focus') {
                    org_elem.bind('focus.tipTip', function () {
                        activate();
                    }).bind('blur.tipTip', function () {
                        deactivate();
                    });
                } else if (opts.activation == 'click') {
                    org_elem.bind('click.tipTip', function (e) {
                        e.preventDefault();
                        activate();
                        return false;
                    }).bind('mouseleave.tipTip', function () {
                        if (!opts.keepAlive) {
                            deactivate();
                        } else {
                            tiptip_holder.one('mouseleave.tipTip', function () {
                                deactivate();
                            });
                        }
                    });
                } else if (opts.activation == 'manual') {
                    // Nothing to register actually. We decide when to show or hide.
                }
            }

            function activate() {
                if (opts.enter.call(org_elem, callback_data) === false) {
                    return;
                }

                // Get the text and append it in the tiptip_content.
                var org_title;
                if (opts.content) {
                    org_title = $.isFunction(opts.content) ? opts.content.call(org_elem, callback_data) : opts.content;
                } else {
                    org_title = opts.content = org_elem.attr(opts.attribute);
                    org_elem.removeAttr(opts.attribute); //remove original Attribute
                }
                if (!org_title) {
                    return; // don't show tip when no content.
                }

                tiptip_content.html(org_title);
                tiptip_holder.hide().removeAttr('class').css({ 'max-width': opts.maxWidth });
                if (opts.cssClass) {
                    tiptip_holder.addClass(opts.cssClass);
                }

                // Calculate the position of the tooltip.
                position_tiptip();

                // Show the tooltip.
                if (timeout) {
                    clearTimeout(timeout);
                }

                timeout = setTimeout(function () {
                    tiptip_holder.stop(true, true).fadeIn(opts.fadeIn);
                }, opts.delay);

                $(window).bind('resize.tipTip scroll.tipTip', position_tiptip);

                // Ensure clicking on anything makes tipTip deactivate
                $(document).unbind("click.tipTip dblclick.tipTip").bind("click.tiptip dblclick.tiptip", deactivate);


                org_elem.addClass('tiptip_visible'); // Add marker class to easily find the target element with visible tooltip. It will be remove later on deactivate().

                opts.afterEnter.call(org_elem, callback_data);
            }

            function deactivate() {
                if (opts.exit.call(org_elem, callback_data) === false) {
                    return;
                }

                if (timeout) {
                    clearTimeout(timeout);
                }

                tiptip_holder.fadeOut(opts.fadeOut);

                $(window).unbind('resize.tipTip scroll.tipTip');
                $(document).unbind("click.tipTip").unbind("dblclick.tipTip");
                    
                org_elem.removeClass('tiptip_visible');

                opts.afterExit.call(org_elem, callback_data);
            }

            function position_tiptip() {
                var org_offset = org_elem.offset(),
                    org_top = org_offset.top,
                    org_left = org_offset.left,
                    org_width = org_elem.outerWidth(),
                    org_height = org_elem.outerHeight(),
                    tip_top,
                    tip_left,
                    tip_width = tiptip_holder.outerWidth(),
                    tip_height = tiptip_holder.outerHeight(),
                    tip_class,
                    tip_classes = { top: 'tip_top', bottom: 'tip_bottom', left: 'tip_left', right: 'tip_right' },
                    arrow_top,
                    arrow_left,
                    arrow_width = 12, // tiptip_arrow.outerHeight() and tiptip_arrow.outerWidth() don't work because they need the element to be visible.
                    arrow_height = 12,
                    win = $(window),
                    win_top = win.scrollTop(),
                    win_left = win.scrollLeft(),
                    win_width = win.width(),
                    win_height = win.height(),
                    is_rtl = opts.detectTextDir && isRtlText(tiptip_content.text());

                function moveTop() {
                    tip_class = tip_classes.top;
                    tip_top = org_top - tip_height - opts.edgeOffset - (arrow_height / 2);
                    tip_left = org_left + ((org_width - tip_width) / 2);
                }

                function moveBottom() {
                    tip_class = tip_classes.bottom;
                    tip_top = org_top + org_height + opts.edgeOffset + (arrow_height / 2);
                    tip_left = org_left + ((org_width - tip_width) / 2);
                }

                function moveLeft() {
                    tip_class = tip_classes.left;
                    tip_top = org_top + ((org_height - tip_height) / 2);
                    tip_left = org_left - tip_width - opts.edgeOffset - (arrow_width / 2);
                }

                function moveRight() {
                    tip_class = tip_classes.right;
                    tip_top = org_top + ((org_height - tip_height) / 2);
                    tip_left = org_left + org_width + opts.edgeOffset + (arrow_width / 2);
                }

                // Calculate the position of the tooltip.
                if (opts.defaultPosition == 'bottom') {
                    moveBottom();
                } else if (opts.defaultPosition == 'top') {
                    moveTop();
                } else if (opts.defaultPosition == 'left' && !is_rtl) {
                    moveLeft();
                } else if (opts.defaultPosition == 'left' && is_rtl) {
                    moveRight();
                } else if (opts.defaultPosition == 'right' && !is_rtl) {
                    moveRight();
                } else if (opts.defaultPosition == 'right' && is_rtl) {
                    moveLeft();
                } else {
                    moveBottom();
                }

                // Flip the tooltip if off the window's viewport. (left <-> right and top <-> bottom).
                if (tip_class == tip_classes.left && !is_rtl && tip_left < win_left) {
                    moveRight();
                } else if (tip_class == tip_classes.left && is_rtl && tip_left - tip_width < win_left) {
                    moveRight();
                } else if (tip_class == tip_classes.right && !is_rtl && tip_left > win_left + win_width) {
                    moveLeft();
                } else if (tip_class == tip_classes.right && is_rtl && tip_left + tip_width > win_left + win_width) {
                    moveLeft();
                } else if (tip_class == tip_classes.top && tip_top < win_top) {
                    moveBottom();
                } else if (tip_class == tip_classes.bottom && tip_top > win_top + win_height) {
                    moveTop();
                }

                // Fix the vertical position if the tooltip is off the top or bottom sides of the window's viewport.
                if (tip_class == tip_classes.left || tip_class == tip_classes.right) { // If positioned left or right check if the tooltip is off the top or bottom window's viewport.
                    if (tip_top + tip_height > win_height + win_top) { // If the bottom edge of the tooltip is off the bottom side of the window's viewport. 
                        tip_top = org_top + org_height > win_height + win_top ? org_top + org_height - tip_height : win_height + win_top - tip_height; // Make 'bottom edge of the tooltip' == 'bottom side of the window's viewport'.
                    } else if (tip_top < win_top) { // If the top edge of the tooltip if off the top side of the window's viewport.
                        tip_top = org_top < win_top ? org_top : win_top; // Make 'top edge of the tooltip' == 'top side of the window's viewport'.
                    }
                }

                // Fix the horizontal position if the tooltip is off the right or left sides of the window's viewport.
                if (tip_class == tip_classes.top || tip_class == tip_classes.bottom) {
                    if (tip_left + tip_width > win_width + win_left) { // If the right edge of the tooltip is off the right side of the window's viewport. 
                        tip_left = org_left + org_width > win_width + win_left ? org_left + org_width - tip_width : win_width + win_left - tip_width; // Make 'right edge of the tooltip' == 'right side of the window's viewport'.
                    } else if (tip_left < win_left) { // If the left edge of the tooltip if off the left side of the window's viewport.
                        tip_left = org_left < win_left ? org_left : win_left; // Make 'left edge of the tooltip' == 'left side of the window's viewport'.
                    }
                }

                // Apply the new position.
                tiptip_holder
                    .css({ left: Math.round(tip_left), top: Math.round(tip_top) })
                    .removeClass(tip_classes.top)
                    .removeClass(tip_classes.bottom)
                    .removeClass(tip_classes.left)
                    .removeClass(tip_classes.right)
                    .addClass(tip_class);

                // Position the arrow
                if (tip_class == tip_classes.top) {
                    arrow_top = tip_height; // Position the arrow vertically on the top of the tooltip.
                    arrow_left = org_left - tip_left + ((org_width - arrow_width) / 2); // Center the arrow horizontally on the center of the target element.
                } else if (tip_class == tip_classes.bottom) {
                    arrow_top = -arrow_height; // Position the arrow vertically on the bottom of the tooltip.
                    arrow_left = org_left - tip_left + ((org_width - arrow_width) / 2); // Center the arrow horizontally on the center of the target element.
                } else if (tip_class == tip_classes.left) {
                    arrow_top = org_top - tip_top + ((org_height - arrow_height) / 2); // Center the arrow vertically on the center of the target element.
                    arrow_left = tip_width; // Position the arrow vertically on the left of the tooltip.
                } else if (tip_class == tip_classes.right) {
                    arrow_top = org_top - tip_top + ((org_height - arrow_height) / 2); // Center the arrow vertically on the center of the target element.
                    arrow_left = -arrow_width; // Position the arrow vertically on the right of the tooltip.
                }

                tiptip_arrow
                    .css({ left: Math.round(arrow_left), top: Math.round(arrow_top) });
            }
        });
    }

    var ltrChars = 'A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02B8\u0300-\u0590\u0800-\u1FFF\u2C00-\uFB1C\uFDFE-\uFE6F\uFEFD-\uFFFF',
        rtlChars = '\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC',
        rtlDirCheckRe = new RegExp('^[^' + ltrChars + ']*[' + rtlChars + ']');

    function isRtlText(text) {
        return rtlDirCheckRe.test(text);
    };

})(jQuery);

