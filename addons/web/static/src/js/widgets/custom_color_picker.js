odoo.define('web.CustomColorPicker', function (require) {
"use strict";

var Widget = require('web.Widget');
var core = require('web.core');

var _t = core._t;

var CustomColorPicker = Widget.extend({
    template: 'customColorPicker',
    xmlDependencies: ['/web/static/src/xml/custom_color_picker.xml'],
    events: _.extend({} , Widget.prototype.events, {
        'mousedown .colorContainer > .table' : '_onMouseDown',
        'mouseup .colorContainer > .table' : '_onMouseUp',
        'change .hexInput input': '_onChangeHex',
        'change .hslInput input': '_onChangeHSL',
    }),

    init: function (parent) {
        this._super.apply(this, arguments);
        this.h = 0;
        this.s = 100;
        this.l = 50;
    },

    start: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.setHueColor();
        this.setColorPalette();
        this.setPreview();
    },

    setPositionOfArrow: function () {
        var arrow = '<div class="downArrow"/><div class="upArrow"/>';
        this.$('.downArrow, .upArrow').remove();
        var $target = this.$('.huetable [data-id="' + this.h + '"]')[0];
        if ($target) {
            this.$('.huetable [data-id="' + this.h + '"]').before($(arrow));
        } else {
            this.$('.huetable [data-id="' + (this.h + 1) + '"]').before($(arrow));
        }
        this.$('.saturationtable [data-id="' + this.s + '"]').before($(arrow));
        this.$('.lightnesstable [data-id="' + this.l + '"]').before($(arrow));
    },

    setColorPalette: function () {
        var self = this;
        this.$('.saturationtable, .lightnesstable').remove();
        _.each(['saturation', 'lightness'], function (aspects) {
            var $colorPalette = $('<table/>', {class: aspects + 'table table'});
            var h = self.h;
            var s = 100;
            var l = 50;
            _.each(_.range(0, 101), function (no) {
                if (aspects === 'saturation') {
                    s = no;
                } else {
                    l = no;
                };
                $colorPalette.append($("<td class='test' data-id= '" + no + "' style = 'background-color: hsl(" + h + ", " + s + "%, " + l + "%); padding:2px'/>"));
            });
            self.$('.' + aspects + '.colorContainer').append($colorPalette);
        })
    },

    setHueColor: function () {
        var $colorPalette = $('<table/>', {class: 'huetable table'});
        _.each(_.range(0, 361, 2), function (no) {
            $colorPalette.append($("<td data-id= '" + no + "' style = 'background-color: hsl(" + no + ", 100%, 50%); padding:1px'/>"));
        });
        $colorPalette.appendTo(this.$('.hue.colorContainer'));
    },

    _onMouseDown: function (ev) {
        var self = this;
        var $currentTarget = $(ev.currentTarget);
        $currentTarget.on('mousemove', function (ev) {
            self.drag = true;
            self.updateValue($(ev.target));
        });
    },

    _onMouseUp: function (ev) {
        var $currentTarget = $(ev.currentTarget);
        $currentTarget.off('mousemove');
        if (this.drag) {
            this.drag = false;
            return;
        }
        this.updateValue($(ev.target));
    },

    updateValue: function ($target) {
        if ($target.parent().hasClass('huetable')) {
            this.h = $target.data('id');
            this.setColorPalette();
        } else if ($target.parent().hasClass('saturationtable')){
            this.s = $target.data('id');
        } else {
            this.l = $target.data('id');
        }
        this.setPreview();
    },

    setPreviewColor: function () {
        this.$('.previewColor').css('background-color', this.hex);
    },

    setHSLInput: function () {
        this.$('.hslInput input.h').val(this.h);
        this.$('.hslInput input.s').val(this.s);
        this.$('.hslInput input.l').val(this.l);
    },

    setPreview: function () {
        this.HSLtoRGB();
        this.RGBtoHEX();
        this.setHSLInput();
        this.$('.hexInput input').val(this.hex);
        this.setPositionOfArrow();
        this.setPreviewColor();
    },

    _onChangeHex: function (ev) {
        var hex = ev.target.value;
        if (hex.length === 7 && hex.match('^#')) {
            this.hex = hex;
            this.setPreviewColor();
            this.HEXtoRGB();
            this.RGBtoHSL();
            this.setHSLInput();
            this.setColorPalette();
            this.setPositionOfArrow();
        }
    },

    _onChangeHSL: function (ev) {
        var $target = $(ev.target);
        if (!$target.hasClass('h') && $target.val() > 100) {
            $target.val('');
            return
        }
        if ($target.hasClass('h')) {
            this.h = $target.val();
            this.setColorPalette();
        } else if ($target.hasClass('s')) {
            this.s = $target.val();
        } else {
            this.l = $target.val();
        }
        this.HSLtoRGB();
        this.RGBtoHEX();
        this.$('.hexInput input').val(this.hex);
        this.setPreviewColor();
        this.setPositionOfArrow();
    },

    HSLtoRGB: function () {
        var r, g, b;
        var L = this.l/100;
        var S = this.s/100;
        var H = this.h/60;
        if (L === 0) {
            this.r = this.g= this.b = 0;
            return 'rgb(0, 0, 0)';
        }
        if (S === 0) {
            this.r = this.g = this.b = Math.abs(L * 255);
            return 'rgb(' + this.r + ',' + this.g + ',' + this.b + ')';
        } else {
            var C = (1 - Math.abs(2 * L - 1)) * S;
            var X = C * (1 - Math.abs((H % 2)- 1));
            var M = L - (C / 2);
            var rgb;
            var c = Math.round((C + M) * 255);
            var x = Math.round((X + M) * 255);
            var m = Math.round(M * 255);
            if (H < 1) rgb = {r: c, g: x, b: m};
            else if (H < 2) rgb = {r: x, g: c, b:m};
            else if (H < 3) rgb = {r: m, g: c, b:x};
            else if (H < 4) rgb = {r: m, g: x, b:c};
            else if (H < 5) rgb = {r: x, g: m, b:c};
            else if (H < 6) rgb = {r: c, g: m, b:x};

            this.r = rgb.r;
            this.g = rgb.g;
            this.b = rgb.b;
            return 'rgb(' + this.r + ',' + this.g + ',' + this.b + ')';
        }
    },

    RGBtoHEX: function () {
        var hex1 = (this.r).toString(16);
        var hex2 = (this.g).toString(16);
        var hex3 = (this.b).toString(16);

        this.hex = "#"+ (
            (hex1.length == 1 ? "0"+ hex1 : hex1) +
            (hex2.length == 1 ? "0"+ hex2 : hex2) +
            (hex3.length == 1 ? "0"+ hex3 : hex3)
        );
        return this.hex;
    },

    HEXtoRGB: function () {
        var r = this.hex.slice(1, 3);
        var g = this.hex.slice(3, 5);
        var b = this.hex.slice(5, 7);
        this.r = parseInt(r, 16);
        this.g = parseInt(g, 16);
        this.b = parseInt(b, 16);
        return 'rgb(' + this.r + ',' + this.g + ',' + this.b + ')';
    },

    RGBtoHSL: function () {
        var p = 255;
        var r = this.r/p;
        var g = this.g/p;
        var b = this.b/p;
        var max = Math.max(r, g, b);
        var min = Math.min(r, g, b);
        var C = max - min;
        if (C === 0) {
            this.h = this.s = 0;
            this.l = Math.round(max * 100);
        } else {
            var l = (max + min) / 2;
            this.l = Math.round(l * 100);
            this.s = Math.round(C / (1 - Math.abs(2 * l - 1)) * 100);
            if (max === r) {
                var h = (g - b) / C % 6;
            } else if (max === g) {
                var h = (b - r) / C + 2;
            } else {
                var h = (r - g) / C + 4;
            }

            if (h < 0) {
                this.h = 360 + Math.round(h * 60);
            } else {
                this.h = Math.round(h * 60);
            }
        }
    },

});

return CustomColorPicker;

});
