/*!
 * Bootstrap Colorpicker
 * http://mjolnic.github.io/bootstrap-colorpicker/
 *
 * Originally written by (c) 2012 Stefan Petre
 * Licensed under the Apache License v2.0
 * http://www.apache.org/licenses/LICENSE-2.0.txt
 *
 * @todo Update DOCS
 */

(function(factory) {
        "use strict";
        if (typeof define === 'function' && define.amd) {
            define(['jquery'], factory);
        } else if (window.jQuery && !window.jQuery.fn.colorpicker) {
            factory(window.jQuery);
        }
    }
    (function($) {
        'use strict';

        '{{color}}';

        var defaults = {
            horizontal: false, // horizontal mode layout ?
            inline: false, //forces to show the colorpicker as an inline element
            color: false, //forces a color
            format: false, //forces a format
            input: 'input', // children input selector
            container: false, // container selector
            component: '.add-on, .input-group-addon', // children component selector
            sliders: {
                saturation: {
                    maxLeft: 100,
                    maxTop: 100,
                    callLeft: 'setSaturation',
                    callTop: 'setBrightness'
                },
                hue: {
                    maxLeft: 0,
                    maxTop: 100,
                    callLeft: false,
                    callTop: 'setHue'
                },
                alpha: {
                    maxLeft: 0,
                    maxTop: 100,
                    callLeft: false,
                    callTop: 'setAlpha'
                }
            },
            slidersHorz: {
                saturation: {
                    maxLeft: 100,
                    maxTop: 100,
                    callLeft: 'setSaturation',
                    callTop: 'setBrightness'
                },
                hue: {
                    maxLeft: 100,
                    maxTop: 0,
                    callLeft: 'setHue',
                    callTop: false
                },
                alpha: {
                    maxLeft: 100,
                    maxTop: 0,
                    callLeft: 'setAlpha',
                    callTop: false
                }
            },
            template: '<div class="colorpicker dropdown-menu">' +
                '<div class="colorpicker-saturation"><i><b></b></i></div>' +
                '<div class="colorpicker-hue"><i></i></div>' +
                '<div class="colorpicker-alpha"><i></i></div>' +
                // '<div class="colorpicker-color"><div /></div>' +
                '</div>'
        };

        var Colorpicker = function(element, options) {
            this.element = $(element).addClass('colorpicker-element');
            this.options = $.extend({}, defaults, this.element.data(), options);
            this.component = this.options.component;
            this.component = (this.component !== false) ? this.element.find(this.component) : false;
            if (this.component && (this.component.length === 0)) {
                this.component = false;
            }
            this.container = (this.options.container === true) ? this.element : this.options.container;
            this.container = (this.container !== false) ? $(this.container) : false;

            // Is the element an input? Should we search inside for any input?
            this.input = this.element.is('input') ? this.element : (this.options.input ?
                this.element.find(this.options.input) : false);
            if (this.input && (this.input.length === 0)) {
                this.input = false;
            }
            // Set HSB color
            this.color = new Color(this.options.color !== false ? this.options.color : this.getValue());
            this.format = this.options.format !== false ? this.options.format : this.color.origFormat;

            // Setup picker
            this.picker = $(this.options.template);
            if (this.options.inline) {
                this.picker.addClass('colorpicker-inline colorpicker-visible');
            } else {
                this.picker.addClass('colorpicker-hidden');
            }
            if (this.options.horizontal) {
                this.picker.addClass('colorpicker-horizontal');
            }
            if (this.format === 'rgba' || this.format === 'hsla') {
                this.picker.addClass('colorpicker-with-alpha');
            }
            if (this.options.align === 'right') {
                this.picker.addClass('colorpicker-right');
            }
            this.picker.on('mousedown.colorpicker touchstart.colorpicker', $.proxy(this.mousedown, this));
            this.picker.appendTo(this.container ? this.container : $('body'));

            // Bind events
            if (this.input !== false) {
                this.input.on({
                    'keyup.colorpicker': $.proxy(this.keyup, this)
                });
                if (this.component === false) {
                    this.element.on({
                        'focus.colorpicker': $.proxy(this.show, this)
                    });
                }
                if (this.options.inline === false) {
                    this.element.on({
                        'focusout.colorpicker': $.proxy(this.hide, this)
                    });
                }
            }

            if (this.component !== false) {
                this.component.on({
                    'click.colorpicker': $.proxy(this.show, this)
                });
            }

            if ((this.input === false) && (this.component === false)) {
                this.element.on({
                    'click.colorpicker': $.proxy(this.show, this)
                });
            }

            // for HTML5 input[type='color']
            if ((this.input !== false) && (this.component !== false) && (this.input.attr('type') === 'color')) {

                this.input.on({
                    'click.colorpicker': $.proxy(this.show, this),
                    'focus.colorpicker': $.proxy(this.show, this)
                });
            }
            this.update();

            $($.proxy(function() {
                this.element.trigger('create');
            }, this));
        };

        Colorpicker.Color = Color;

        Colorpicker.prototype = {
            constructor: Colorpicker,
            destroy: function() {
                this.picker.remove();
                this.element.removeData('colorpicker').off('.colorpicker');
                if (this.input !== false) {
                    this.input.off('.colorpicker');
                }
                if (this.component !== false) {
                    this.component.off('.colorpicker');
                }
                this.element.removeClass('colorpicker-element');
                this.element.trigger({
                    type: 'destroy'
                });
            },
            reposition: function() {
                if (this.options.inline !== false || this.options.container) {
                    return false;
                }
                var type = this.container && this.container[0] !== document.body ? 'position' : 'offset';
                var element = this.component || this.element;
                var offset = element[type]();
                if (this.options.align === 'right') {
                    offset.left -= this.picker.outerWidth() - element.outerWidth()
                }
                this.picker.css({
                    top: offset.top + element.outerHeight(),
                    left: offset.left
                });
            },
            show: function(e) {
                if (this.isDisabled()) {
                    return false;
                }
                this.picker.addClass('colorpicker-visible').removeClass('colorpicker-hidden');
                this.reposition();
                $(window).on('resize.colorpicker', $.proxy(this.reposition, this));
                if (e && (!this.hasInput() || this.input.attr('type') === 'color')) {
                    if (e.stopPropagation && e.preventDefault) {
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
                if (this.options.inline === false) {
                    $(window.document).on({
                        'mousedown.colorpicker': $.proxy(this.hide, this)
                    });
                }
                this.element.trigger({
                    type: 'showPicker',
                    color: this.color
                });
            },
            hide: function() {
                this.picker.addClass('colorpicker-hidden').removeClass('colorpicker-visible');
                $(window).off('resize.colorpicker', this.reposition);
                $(document).off({
                    'mousedown.colorpicker': this.hide
                });
                this.update();
                this.element.trigger({
                    type: 'hidePicker',
                    color: this.color
                });
            },
            updateData: function(val) {
                val = val || this.color.toString(this.format);
                this.element.data('color', val);
                return val;
            },
            updateInput: function(val) {
                val = val || this.color.toString(this.format);
                if (this.input !== false) {
                    this.input.prop('value', val);
                }
                return val;
            },
            updatePicker: function(val) {
                if (val !== undefined) {
                    this.color = new Color(val);
                }
                var sl = (this.options.horizontal === false) ? this.options.sliders : this.options.slidersHorz;
                var icns = this.picker.find('i');
                if (icns.length === 0) {
                    return;
                }
                if (this.options.horizontal === false) {
                    sl = this.options.sliders;
                    icns.eq(1).css('top', sl.hue.maxTop * (1 - this.color.value.h)).end()
                        .eq(2).css('top', sl.alpha.maxTop * (1 - this.color.value.a));
                } else {
                    sl = this.options.slidersHorz;
                    icns.eq(1).css('left', sl.hue.maxLeft * (1 - this.color.value.h)).end()
                        .eq(2).css('left', sl.alpha.maxLeft * (1 - this.color.value.a));
                }
                icns.eq(0).css({
                    'top': sl.saturation.maxTop - this.color.value.b * sl.saturation.maxTop,
                    'left': this.color.value.s * sl.saturation.maxLeft
                });
                this.picker.find('.colorpicker-saturation').css('backgroundColor', this.color.toHex(this.color.value.h, 1, 1, 1));
                this.picker.find('.colorpicker-alpha').css('backgroundColor', this.color.toHex());
                this.picker.find('.colorpicker-color, .colorpicker-color div').css('backgroundColor', this.color.toString(this.format));
                return val;
            },
            updateComponent: function(val) {
                val = val || this.color.toString(this.format);
                if (this.component !== false) {
                    var icn = this.component.find('i').eq(0);
                    if (icn.length > 0) {
                        icn.css({
                            'backgroundColor': val
                        });
                    } else {
                        this.component.css({
                            'backgroundColor': val
                        });
                    }
                }
                return val;
            },
            update: function(force) {
                var val;
                if ((this.getValue(false) !== false) || (force === true)) {
                    // Update input/data only if the current value is not empty
                    val = this.updateComponent();
                    this.updateInput(val);
                    this.updateData(val);
                    this.updatePicker(); // only update picker if value is not empty
                }
                return val;

            },
            setValue: function(val) { // set color manually
                this.color = new Color(val);
                this.update();
                this.element.trigger({
                    type: 'changeColor',
                    color: this.color,
                    value: val
                });
            },
            getValue: function(defaultValue) {
                defaultValue = (defaultValue === undefined) ? '#000000' : defaultValue;
                var val;
                if (this.hasInput()) {
                    val = this.input.val();
                } else {
                    val = this.element.data('color');
                }
                if ((val === undefined) || (val === '') || (val === null)) {
                    // if not defined or empty, return default
                    val = defaultValue;
                }
                return val;
            },
            hasInput: function() {
                return (this.input !== false);
            },
            isDisabled: function() {
                if (this.hasInput()) {
                    return (this.input.prop('disabled') === true);
                }
                return false;
            },
            disable: function() {
                if (this.hasInput()) {
                    this.input.prop('disabled', true);
                    this.element.trigger({
                        type: 'disable',
                        color: this.color,
                        value: this.getValue()
                    });
                    return true;
                }
                return false;
            },
            enable: function() {
                if (this.hasInput()) {
                    this.input.prop('disabled', false);
                    this.element.trigger({
                        type: 'enable',
                        color: this.color,
                        value: this.getValue()
                    });
                    return true;
                }
                return false;
            },
            currentSlider: null,
            mousePointer: {
                left: 0,
                top: 0
            },
            mousedown: function(e) {
                if (!e.pageX && !e.pageY && e.originalEvent) {
                    e.pageX = e.originalEvent.touches[0].pageX;
                    e.pageY = e.originalEvent.touches[0].pageY;
                }
                e.stopPropagation();
                e.preventDefault();

                var target = $(e.target);

                //detect the slider and set the limits and callbacks
                var zone = target.closest('div');
                var sl = this.options.horizontal ? this.options.slidersHorz : this.options.sliders;
                if (!zone.is('.colorpicker')) {
                    if (zone.is('.colorpicker-saturation')) {
                        this.currentSlider = $.extend({}, sl.saturation);
                    } else if (zone.is('.colorpicker-hue')) {
                        this.currentSlider = $.extend({}, sl.hue);
                    } else if (zone.is('.colorpicker-alpha')) {
                        this.currentSlider = $.extend({}, sl.alpha);
                    } else {
                        return false;
                    }
                    var offset = zone.offset();
                    //reference to guide's style
                    this.currentSlider.guide = zone.find('i')[0].style;
                    this.currentSlider.left = e.pageX - offset.left;
                    this.currentSlider.top = e.pageY - offset.top;
                    this.mousePointer = {
                        left: e.pageX,
                        top: e.pageY
                    };
                    //trigger mousemove to move the guide to the current position
                    $(document).on({
                        'mousemove.colorpicker': $.proxy(this.mousemove, this),
                        'touchmove.colorpicker': $.proxy(this.mousemove, this),
                        'mouseup.colorpicker': $.proxy(this.mouseup, this),
                        'touchend.colorpicker': $.proxy(this.mouseup, this)
                    }).trigger('mousemove');
                }
                return false;
            },
            mousemove: function(e) {
                if (!e.pageX && !e.pageY && e.originalEvent) {
                    e.pageX = e.originalEvent.touches[0].pageX;
                    e.pageY = e.originalEvent.touches[0].pageY;
                }
                e.stopPropagation();
                e.preventDefault();
                var left = Math.max(
                    0,
                    Math.min(
                        this.currentSlider.maxLeft,
                        this.currentSlider.left + ((e.pageX || this.mousePointer.left) - this.mousePointer.left)
                    )
                );
                var top = Math.max(
                    0,
                    Math.min(
                        this.currentSlider.maxTop,
                        this.currentSlider.top + ((e.pageY || this.mousePointer.top) - this.mousePointer.top)
                    )
                );
                this.currentSlider.guide.left = left + 'px';
                this.currentSlider.guide.top = top + 'px';
                if (this.currentSlider.callLeft) {
                    this.color[this.currentSlider.callLeft].call(this.color, left / this.currentSlider.maxLeft);
                }
                if (this.currentSlider.callTop) {
                    this.color[this.currentSlider.callTop].call(this.color, top / this.currentSlider.maxTop);
                }
                this.update(true);

                this.element.trigger({
                    type: 'changeColor',
                    color: this.color
                });
                return false;
            },
            mouseup: function(e) {
                e.stopPropagation();
                e.preventDefault();
                $(document).off({
                    'mousemove.colorpicker': this.mousemove,
                    'touchmove.colorpicker': this.mousemove,
                    'mouseup.colorpicker': this.mouseup,
                    'touchend.colorpicker': this.mouseup
                });
                return false;
            },
            keyup: function(e) {
                if ((e.keyCode === 38)) {
                    if (this.color.value.a < 1) {
                        this.color.value.a = Math.round((this.color.value.a + 0.01) * 100) / 100;
                    }
                    this.update(true);
                } else if ((e.keyCode === 40)) {
                    if (this.color.value.a > 0) {
                        this.color.value.a = Math.round((this.color.value.a - 0.01) * 100) / 100;
                    }
                    this.update(true);
                } else {
                    var val = this.input.val();
                    this.color = new Color(val);
                    if (this.getValue(false) !== false) {
                        this.updateData();
                        this.updateComponent();
                        this.updatePicker();
                    }
                }
                this.element.trigger({
                    type: 'changeColor',
                    color: this.color,
                    value: val
                });
            }
        };

        $.colorpicker = Colorpicker;

        $.fn.colorpicker = function(option) {
            var pickerArgs = arguments,
                rv;

            var $returnValue = this.each(function() {
                var $this = $(this),
                    inst = $this.data('colorpicker'),
                    options = ((typeof option === 'object') ? option : {});
                if ((!inst) && (typeof option !== 'string')) {
                    $this.data('colorpicker', new Colorpicker(this, options));
                } else {
                    if (typeof option === 'string') {
                        rv = inst[option].apply(inst, Array.prototype.slice.call(pickerArgs, 1));
                    }
                }
            });
            if (option === 'getValue') {
                return rv;
            }
            return $returnValue;
        };

        $.fn.colorpicker.constructor = Colorpicker;

    }));
