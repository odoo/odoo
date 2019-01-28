odoo.define('web_editor.wysiwyg.plugin.font', function (require) {
'use strict';

var core = require('web.core');
var ColorpickerDialog = require('wysiwyg.widgets.ColorpickerDialog');
var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');
var wysiwygTranslation = require('web_editor.wysiwyg.translation');
var wysiwygOptions = require('web_editor.wysiwyg.options');

var QWeb = core.qweb;
var _t = core._t;

var dom = $.summernote.dom;

//--------------------------------------------------------------------------
// Font (colorpicker & font-size)
//--------------------------------------------------------------------------

dom.isFont = function (node) {
    return node && node.tagName === "FONT" || dom.isIcon(node);
};

var FontPlugin = AbstractPlugin.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Creates both ColorPicker buttons (fore- and backcolors) containing their palettes.
     *
     * @returns {jQuery} the buttons' div.btn-group container
     */
    createColorPickerButtons: function () {
        var self = this;
        var $container = $('<div class="note-btn-group btn-group note-color"/>');

        // create and append the buttons

        this._createForeColorButton().appendTo($container);
        this._createBackColorButton().appendTo($container);

        // add event

        $container.on('mousedown', function () {
            self.context.invoke('editor.saveRange');
        });
        return $container;
    },
    /**
     * Takes the font size button created by summernote and override its
     * events so as to customize its behavior.
     *
     * @param {jQuery} $button the button, as created by summernote
     * @returns {jQuery} the overridden button
     */
    overrideFontSizeButton: function ($button) {
        var self = this;
        $button.click(function (e) {
            e.preventDefault();
        });
        $button.find('.dropdown-menu').off('click').on('mousedown', function (e) {
            e.preventDefault();
            self.context.invoke('editor.createRange');
            self.context.invoke('editor.beforeCommand');
            var $target = $(e.target);
            self.context.invoke('FontPlugin.changeFontSize', $target.closest('[data-value]').data('value'), $target);
            self.context.invoke('buttons.updateCurrentStyle');
            self.context.invoke('editor.saveRange');
            self.context.invoke('editor.afterCommand');
        });
        return $button;
    },
    /**
     * Creates a (fore- or back-) color palette.
     *
     * @param {string('foreColor'|'backColor')} eventName
     * @returns {jQuery}
     */
    createPalette: function (eventName) {
        var self = this;
        var colors = _.clone(this.options.colors);
        colors.splice(0, 1); // Ignore the summernote gray palette and use ours
        var $palette = $(QWeb.render('wysiwyg.plugin.font.colorPalette', {
            colors: colors,
            eventName: eventName,
            lang: this.lang,
        }));
        if (this.options.tooltip) {
            $palette.find('.note-color-btn').tooltip({
                container: this.options.container,
                trigger: 'hover',
                placement: 'bottom'
            });
        }

        // custom structure for the color picker and custom colorsin XML template
        var $clpicker = $(QWeb.render('web_editor.colorpicker'));

        var $buttons = $(_.map($clpicker.children(), function (group) {
            var $contents = $(group).contents();
            if (!$contents.length) {
                return '';
            }
            var $row = $("<div/>", {
                "class": "note-color-row mb8 clearfix",
                'data-group': $(group).data('name'),
            }).append($contents);
            var $after_breaks = $row.find(".o_small + :not(.o_small)");
            if ($after_breaks.length === 0) {
                $after_breaks = $row.find(":nth-child(8n+9)");
            }
            $after_breaks.addClass("o_clear");
            return $row[0].outerHTML;
        }).join(""));

        $buttons.find('button').each(function () {
            var color = $(this).data('color');
            $(this).addClass('note-color-btn bg-' + color).attr('data-value', (eventName === 'backColor' ? 'bg-' : 'text-') + color);
        });

        $palette.find('.o_theme_color_placeholder').prepend($buttons.filter('[data-group="theme"]'));
        $palette.find('.o_transparent_color_placeholder').prepend($buttons.filter('[data-group="transparent_grayscale"]'));
        $palette.find('.o_common_color_placeholder').prepend($buttons.filter('[data-group="common"]'));

        $palette.off('click').on('mousedown', '.note-color-btn', function (e) {
            e.preventDefault();
            self.context.invoke('editor.createRange');
            self.context.invoke('editor.beforeCommand');
            var method = eventName === 'backColor' ? 'changeBgColor' : 'changeForeColor';
            var $target = $(e.target);
            self.context.invoke('FontPlugin.' + method, $target.closest('[data-value]').data('value'), $target);
            self.context.invoke('buttons.updateCurrentStyle');
            self.editable.normalize();
            self.context.invoke('editor.saveRange');
            self.context.invoke('editor.afterCommand');
        });
        $palette.on('mousedown', '.note-custom-color', this._onCustomColor.bind(this, eventName));

        return $palette;
    },
    /**
     * Change the selection's fore color.
     *
     * @param {string} color (hexadecimal or class name)
     */
    changeForeColor: function (color) {
        this._applyFont(color || 'text-undefined', null, null);
    },
    /**
     * Change the selection's background color.
     *
     * @param {string} color (hexadecimal or class name)
     */
    changeBgColor: function (color) {
        this._applyFont(null, color || 'bg-undefined', null);
    },
    /**
     * Change the selection's font size.
     *
     * @param {integer} fontsize
     */
    changeFontSize: function (fontsize) {
        this._applyFont(null, null, fontsize || 'inherit');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Applies the given styles (fore- or backcolor, font size)
     * to a given <font> node.
     *
     * @private
     * @param {Node} node
     * @param {string} color (hexadecimal or class name)
     * @param {string} bgcolor (hexadecimal or class name)
     * @param {integer} size
     * @returns {Node} the <font> node
     */
    _applyStylesToFontNode: function (node, color, bgcolor, size) {
        var className = node.className.split(this.context.invoke('HelperPlugin.getRegex', 'space'));
        var k;
        if (color) {
            for (k = 0; k < className.length; k++) {
                if (className[k].length && className[k].slice(0, 5) === "text-") {
                    className.splice(k, 1);
                    k--;
                }
            }
            if (color === 'text-undefined') {
                node.className = className.join(" ");
                node.style.color = "inherit";
            } else if (color.indexOf('text-') !== -1) {
                node.className = className.join(" ") + " " + color;
                node.style.color = "inherit";
            } else {
                node.className = className.join(" ");
                node.style.color = color;
            }
        }
        if (bgcolor) {
            for (k = 0; k < className.length; k++) {
                if (className[k].length && className[k].slice(0, 3) === "bg-") {
                    className.splice(k, 1);
                    k--;
                }
            }

            if (bgcolor === 'bg-undefined') {
                node.className = className.join(" ");
                node.style.backgroundColor = "inherit";
            } else if (bgcolor.indexOf('bg-') !== -1) {
                node.className = className.join(" ") + " " + bgcolor;
                node.style.backgroundColor = "inherit";
            } else {
                node.className = className.join(" ");
                node.style.backgroundColor = bgcolor;
            }
        }
        if (size) {
            node.style.fontSize = "inherit";
            if (!isNaN(size) && Math.abs(parseInt(this.window.getComputedStyle(node).fontSize, 10) - size) / size > 0.05) {
                node.style.fontSize = size + "px";
            }
        }
        return node;
    },
    /**
     * Applies the given styles (fore- or backcolor, font size) to the selection.
     * If no text is selected, apply to the current text node, if any.
     *
     * @private
     * @param {string} color (hexadecimal or class name)
     * @param {string} bgcolor (hexadecimal or class name)
     * @param {integer} fontsize
     */
    _applyFont: function (color, bgcolor, size) {
        var self = this;
        var r = this.context.invoke('editor.createRange');
        if (!r || !this.$editable.has(r.sc).length || !this.$editable.has(r.ec).length) {
            return;
        }
        var target;
        var font;
        if (r.isCollapsed()) {
            if (dom.isIcon(r.sc)) {
                target = dom.lastAncestor(r.sc, dom.isIcon);
            } else {
                target = this.context.invoke('editor.restoreTarget');
                if (target && dom.isIcon(target)) {
                    r = this.context.invoke('editor.setRange', target, 0);
                } else if (dom.isText(r.sc)) {
                    font = dom.create("font");
                    font.appendChild(this.document.createTextNode('\u200B'));

                    var fontParent = dom.ancestor(r.sc, function (n) {
                        return n.tagName === 'FONT';
                    });
                    var right;
                    if (fontParent) {
                        right = this.context.invoke('HelperPlugin.splitTree', fontParent, r.getStartPoint());
                    } else {
                        right = r.sc.splitText(r.so);
                    }
                    $(right).before(font);
                    font = this._applyStylesToFontNode(font, color, bgcolor, size);
                    r = this.context.invoke('editor.setRange', font, 1);
                    r.select();
                    return;
                }
            }
        }

        var startPoint = r.getStartPoint();
        var endPoint = r.getEndPoint();
        if (startPoint.node.tagName && startPoint.node.childNodes[startPoint.offset]) {
            startPoint.node = startPoint.node.childNodes[startPoint.offset];
            startPoint.offset = 0;
        }
        if (endPoint.node.tagName && endPoint.node.childNodes[endPoint.offset]) {
            endPoint.node = endPoint.node.childNodes[endPoint.offset];
            endPoint.offset = 0;
        }
        // get first and last point
        var ancestor;
        var node;
        if (!r.isCollapsed()) {
            if (endPoint.offset && endPoint.offset !== dom.nodeLength(endPoint.node)) {
                ancestor = dom.lastAncestor(endPoint.node, dom.isFont) || endPoint.node;
                dom.splitTree(ancestor, endPoint);
            }
            if (startPoint.offset && startPoint.offset !== dom.nodeLength(startPoint.node)) {
                ancestor = dom.lastAncestor(startPoint.node, dom.isFont) || startPoint.node;
                node = dom.splitTree(ancestor, startPoint);
                if (endPoint.node === startPoint.node) {
                    endPoint.node = node;
                    endPoint.offset = dom.nodeLength(node);
                }
                startPoint.node = node;
                startPoint.offset = 0;
            }
        }
        // get list of nodes to change
        var nodes = [];
        dom.walkPoint(startPoint, endPoint, function (point) {
            var node = point.node;
            if (((dom.isText(node) && self.context.invoke('HelperPlugin.isVisibleText', node)) || dom.isIcon(node)) &&
                (node !== endPoint.node || endPoint.offset)) {
                nodes.push(point.node);
            }
        });
        nodes = _.unique(nodes);
        // if fontawesome
        if (r.isCollapsed()) {
            nodes.push(startPoint.node);
        }

        // apply font: foreColor, backColor, size (the color can be use a class text-... or bg-...)
        var $font;
        var fonts = [];
        var style;
        var className;
        var i;
        if (color || bgcolor || size) {
            for (i = 0; i < nodes.length; i++) {
                node = nodes[i];
                font = dom.lastAncestor(node, dom.isFont);
                if (!font) {
                    if (node.textContent.match(this.context.invoke('HelperPlugin.getRegex', 'startAndEndSpace'))) {
                        node.textContent = node.textContent.replace(this.context.invoke('HelperPlugin.getRegex', 'startAndEndSpace', 'g'), '\u00A0');
                    }
                    font = dom.create("font");
                    node.parentNode.insertBefore(font, node);
                    font.appendChild(node);
                }
                fonts.push(font);
                this._applyStylesToFontNode(font, color, bgcolor, size);
            }
        }
        // remove empty values
        // we must remove the value in 2 steps (applay inherit then remove) because some
        // browser like chrome have some time an error for the rendering and/or keep inherit
        for (i = 0; i < fonts.length; i++) {
            font = fonts[i];
            if (font.style.color === "inherit") {
                font.style.color = "";
            }
            if (font.style.backgroundColor === "inherit") {
                font.style.backgroundColor = "";
            }
            if (font.style.fontSize === "inherit") {
                font.style.fontSize = "";
            }
            $font = $(font);
            if (font.style.color === '' && font.style.backgroundColor === '' && font.style.fontSize === '') {
                $font.removeAttr("style");
            }
            if (!font.className.length) {
                $font.removeAttr("class");
            }
        }

        // target the deepest node
        if (startPoint.node.tagName && !startPoint.offset) {
            startPoint.node = this.context.invoke('HelperPlugin.firstLeaf', startPoint.node.childNodes[startPoint.offset] || startPoint.node);
            startPoint.offset = 0;
        }
        if (endPoint.node.tagName && !endPoint.offset) {
            endPoint.node = this.context.invoke('HelperPlugin.firstLeaf', endPoint.node.childNodes[endPoint.offset] || endPoint.node);
            endPoint.offset = 0;
        }

        // select nodes to clean (to remove empty font and merge same nodes)
        nodes = [];
        dom.walkPoint(startPoint, endPoint, function (point) {
            nodes.push(point.node);
        });
        nodes = _.unique(nodes);
        // remove node without attributes (move content), and merge the same nodes
        for (i = 0; i < nodes.length; i++) {
            node = nodes[i];
            if (dom.isText(node) && !this.context.invoke('HelperPlugin.isVisibleText', node)) {
                continue;
            }
            font = dom.lastAncestor(node, dom.isFont);
            node = font || dom.ancestor(node, dom.isSpan);
            if (!node) {
                continue;
            }
            $font = $(node);
            className = this.context.invoke('HelperPlugin.orderClass', node);
            style = this.context.invoke('HelperPlugin.orderStyle', node);
            if (!className && !style) {
                $(node).before($(node).contents());
                if (endPoint.node === node) {
                    endPoint = dom.prevPointUntil(endPoint, function (point) {
                        return point.node !== node;
                    });
                }
                $(node).remove();

                nodes.splice(i, 1);
                i--;
                continue;
            }
            var prev = font && font.previousSibling;
            while (prev && !font.tagName && !this.context.invoke('HelperPlugin.isVisibleText', prev)) {
                prev = prev.previousSibling;
            }
            if (prev &&
                font.tagName === prev.tagName &&
                className === this.context.invoke('HelperPlugin.orderClass', prev) && style === this.context.invoke('HelperPlugin.orderStyle', prev)) {
                $(prev).append($(font).contents());
                if (endPoint.node === font) {
                    endPoint = dom.prevPointUntil(endPoint, function (point) {
                        return point.node !== font;
                    });
                }
                $(font).remove();

                nodes.splice(i, 1);
                i--;
                continue;
            }
        }

        // restore selection
        r = this.context.invoke('editor.setRange', startPoint.node, startPoint.offset, endPoint.node, endPoint.offset);
        r.normalize().select();

        if (target) {
            this.context.invoke('MediaPlugin.updatePopoverAfterEdit', target);
        }
    },
    /**
     * Creates the backcolor button containing its palette.
     *
     * @private
     * @returns {jQuery} the backcolor button
     */
    _createBackColorButton: function () {
        var $bgPalette = this.createPalette('backColor');
        $bgPalette.find("button:not(.note-color-btn)")
            .addClass("note-color-btn")
            .attr('data-event', 'backColor')
            .each(function () {
                var $el = $(this);
                var className = $el.hasClass('o_custom_color') ? $el.data('color') : 'bg-' + $el.data('color');
                $el.attr('data-value', className).addClass($el.hasClass('o_custom_color') ? '' : className);
            });

        var $bgContainer = $(QWeb.render('wysiwyg.plugin.font.paletteButton', {
            className: 'note-bg-color',
            icon: this.options.icons.bg,
        }));
        $bgContainer.find('.dropdown-menu').append($bgPalette);
        return $bgContainer;
    },
    /**
     * Creates the forecolor button containing its palette.
     *
     * @private
     * @returns {jQuery} the forecolor button
     */
    _createForeColorButton: function () {
        var $forePalette = this.createPalette('foreColor');
        $forePalette.find("button:not(.note-color-btn)")
            .addClass("note-color-btn")
            .attr('data-event', 'foreColor')
            .each(function () {
                var $el = $(this);
                var className = $el.hasClass('o_custom_color') ? $el.data('color') : 'text-' + $el.data('color');
                $el.attr('data-value', className).addClass($el.hasClass('o_custom_color') ? '' : 'bg-' + $el.data('color'));
            });

        var $foreContainer = $(QWeb.render('wysiwyg.plugin.font.paletteButton', {
            className: 'note-fore-color',
            icon: this.options.icons.fore,
        }));
        $foreContainer.find('.dropdown-menu').append($forePalette);
        return $foreContainer;
    },
    /**
     * Method called on custom color button click :
     * opens the color picker dialog and saves the chosen color on save.
     *
     * @private
     * @param {string} targetColor
     * @param {jQuery Event} ev
     */
    _onCustomColor: function (targetColor, ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var self = this;
        var $button = $(ev.target).next('button');
        var target = this.context.invoke('editor.restoreTarget');
        var colorPickerDialog = new ColorpickerDialog(this, {});

        this.context.invoke('editor.saveRange');
        colorPickerDialog.on('colorpicker:saved', this, this._wrapCommand(function (ev) {
            $button = $button.clone().appendTo($button.parent());
            $button.show();
            $button.css('background-color', ev.data.cssColor);
            $button.attr('data-value', ev.data.cssColor);
            $button.data('value', ev.data.cssColor);
            $button.attr('title', ev.data.cssColor);
            self.context.invoke('editor.saveTarget', target);
            self.context.invoke('editor.restoreRange');
            $button.mousedown();
        }));
        colorPickerDialog.open();
        this.context.invoke('MediaPlugin.hidePopovers');
    },
});

_.extend(wysiwygOptions.icons, {
    fore: 'fa fa-font',
    bg: 'fa fa-paint-brush',
});
_.extend(wysiwygTranslation.color, {
    customColor: _t('Custom color'),
    fore: _t('Color'),
    bg: _t('Background color'),
});

registry.add('FontPlugin', FontPlugin);

registry.addXmlDependency('/web_editor/static/src/xml/wysiwyg_colorpicker.xml');
registry.addJob(function (wysiwyg) {
    if ('web_editor.colorpicker' in QWeb.templates) {
        return;
    }

    if (wysiwyg.isDestroyed()) {
        throw new Error('The Wysiwyg are destroyed before this loading');
    }

    var options = {};
    wysiwyg.trigger_up('getRecordInfo', {
        recordInfo: options,
        callback: function (recordInfo) {
            _.defaults(options, recordInfo);
        },
    });
    return wysiwyg._rpc({
        model: 'ir.ui.view',
        method: 'read_template',
        args: ['web_editor.colorpicker'],
        kwargs: {
            context: options.context,
        },
    }).then(function (template) {
        if (!/^<templates>/.test(template)) {
            template = _.str.sprintf('<templates>%s</templates>', template);
        }
        QWeb.add_template(template);
    });
});


return FontPlugin;

});
