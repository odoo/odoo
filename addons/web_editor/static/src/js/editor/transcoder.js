odoo.define('web_editor.transcoder', function (require) {
'use strict';

var widget = require('web_editor.widget');

var rulesCache = [];

/**
 * Returns the css rules which applies on an element, tweaked so that they are
 * browser/mail client ok.
 *
 * @param {DOMElement} a
 * @returns {Object} css property name -> css property value
 */
function getMatchedCSSRules(a) {
    var i, r, k;
    if (!rulesCache.length) {
        var sheets = document.styleSheets;
        for (i = sheets.length-1 ; i >= 0 ; i--) {
            var rules;
            if (sheets[i].rules) {
                rules = sheets[i].rules;
            } else {
                // try...catch because Firefox not able to enumerate
                // document.styleSheets[].cssRules[] for cross-domain sheets.
                try {
                    rules = sheets[i].cssRules;
                } catch (e) {
                    console.warn("Can't read the css rules of: " + sheets[i].href, e);
                    continue;
                }
                rules = sheets[i].cssRules;
            }
            if (rules) {
                for (r = rules.length-1; r >= 0; r--) {
                    var selectorText = rules[r].selectorText;
                    if (selectorText &&
                            rules[r].cssText &&
                            selectorText !== '*' &&
                            selectorText.indexOf(':hover') === -1 &&
                            selectorText.indexOf(':before') === -1 &&
                            selectorText.indexOf(':after') === -1 &&
                            selectorText.indexOf(':active') === -1 &&
                            selectorText.indexOf(':link') === -1 &&
                            selectorText.indexOf('::') === -1 &&
                            selectorText.indexOf('"') === -1 &&
                            selectorText.indexOf("'") === -1) {
                        var st = selectorText.split(/\s*,\s*/);
                        for (k = 0 ; k < st.length ; k++) {
                            rulesCache.push({ 'selector': st[k], 'style': rules[r].style });
                        }
                    }
                }
            }
        }
        rulesCache.reverse();
    }

    var css = [];
    var style;
    a.matches = a.matches || a.webkitMatchesSelector || a.mozMatchesSelector || a.msMatchesSelector || a.oMatchesSelector;
    for (r = 0; r < rulesCache.length; r++) {
        if (a.matches(rulesCache[r].selector)) {
            style = rulesCache[r].style;
            if (style.parentRule) {
                var style_obj = {};
                var len;
                for (k = 0, len = style.length ; k < len ; k++) {
                    if (style[k].indexOf('animation') !== -1) {
                        continue;
                    }
                    style_obj[style[k]] = style[style[k].replace(/-(.)/g, function (a, b) { return b.toUpperCase(); })];
                    if (new RegExp(style[k] + '\s*:[^:;]+!important' ).test(style.cssText)) {
                        style_obj[style[k]] += ' !important';
                    }
                }
                rulesCache[r].style = style = style_obj;
            }
            css.push([rulesCache[r].selector, style]);
        }
    }

    function specificity(selector) {
        // http://www.w3.org/TR/css3-selectors/#specificity
        var a = 0;
        selector = selector.replace(/#[a-z0-9_-]+/gi, function () { a++; return ''; });
        var b = 0;
        selector = selector.replace(/(\.[a-z0-9_-]+)|(\[.*?\])/gi, function () { b++; return ''; });
        var c = 0;
        selector = selector.replace(/(^|\s+|:+)[a-z0-9_-]+/gi, function (a) { if (a.indexOf(':not(')===-1) c++; return ''; });
        return a*100 + b*10 + c;
    }
    css.sort(function (a, b) { return specificity(a[0]) - specificity(b[0]); });

    style = {};
    _.each(css, function (v,k) {
        _.each(v[1], function (v,k) {
            if (v && _.isString(v) && k.indexOf('-webkit') === -1 && (!style[k] || style[k].indexOf('important') === -1 || v.indexOf('important') !== -1)) {
                style[k] = v;
            }
        });
    });

    _.each(style, function (v,k) {
        if (v.indexOf('important') !== -1) {
            style[k] = v.slice(0, v.length-11);
        }
    });

    if (style.display === 'block') {
        delete style.display;
    }

    _.each(['margin', 'padding'], function (p) {
        if (style[p+'-top'] || style[p+'-right'] || style[p+'-bottom'] || style[p+'-left']) {
            if (style[p+'-top'] === style[p+'-right'] && style[p+'-top'] === style[p+'-bottom'] && style[p+'-top'] === style[p+'-left']) {
                // keep => property: [top/right/bottom/left value];
                style[p] = style[p+'-top'];
            }
            else {
                // keep => property: [top value] [right value] [bottom value] [left value];
                style[p] = (style[p+'-top'] || 0) + ' ' + (style[p+'-right'] || 0) + ' ' + (style[p+'-bottom'] || 0) + ' ' + (style[p+'-left'] || 0);
                if (style[p].indexOf('inherit') !== -1 || style[p].indexOf('initial') !== -1) {
                    // keep => property-top: [top value]; property-right: [right value]; property-bottom: [bottom value]; property-left: [left value];
                    delete style[p];
                    return;
                }
            }
            delete style[p+'-top'];
            delete style[p+'-right'];
            delete style[p+'-bottom'];
            delete style[p+'-left'];
        }
    });

    // text-decoration rule is decomposed in -line, -color and -style. This is
    // however not supported by many browser/mail clients and the editor does
    // not allow to change -color and -style rule anyway
    if (style['text-decoration-line']) {
        style['text-decoration'] = style['text-decoration-line'];
        delete style['text-decoration-line'];
        delete style['text-decoration-color'];
        delete style['text-decoration-style'];
    }

    return style;
}

/**
 * Converts font icons to images.
 *
 * @param {jQuery} $editable - the element in which the font icons have to be
 *                           converted to images
 */
function fontToImg($editable) {
    $editable.find('.fa').each(function () {
        var $font = $(this);
        var icon, content;
        _.find(widget.fontIcons, function (font) {
            return _.find(widget.getCssSelectors(font.parser), function (css) {
                if ($font.is(css[0].replace(/::?before/g, ''))) {
                    icon = css[2].split('-').shift();
                    content = css[1].match(/content:\s*['"]?(.)['"]?/)[1];
                    return true;
                }
            });
        });
        if (content) {
            var color = $font.css('color').replace(/\s/g, '');
            $font.replaceWith($('<img/>', {
                src: _.str.sprintf('/web_editor/font_to_img/%s/%s/%s', content.charCodeAt(0), window.encodeURI(color), Math.max(1, $font.height())),
                'data-class': $font.attr('class'),
                'data-style': $font.attr('style'),
                class: $font.attr('class').replace(new RegExp('(^|\\s+)' + icon + '(-[^\\s]+)?', 'gi'), ''), // remove inline font-awsome style
                style: $font.attr('style'),
            }).css({height: 'auto', width: 'auto'}));
        } else {
            $font.remove();
        }
    });
}

/**
 * Converts images which were the result of a font icon convertion to a font
 * icon again.
 *
 * @param {jQuery} $editable - the element in which the images will be converted
 *                           back to font icons
 */
function imgToFont($editable) {
    $editable.find('img[src*="/web_editor/font_to_img/"]').each(function () {
        var $img = $(this);
        $img.replaceWith($('<span/>', {
            class: $img.data('class'),
            style: $img.data('style')
        }));
    });
}

/**
 * Converts css style to inline style (leave the classes on elements but forces
 * the style they give as inline style).
 *
 * @param {jQuery} $editable
 */
function classToStyle($editable) {
    if (!rulesCache.length) {
        getMatchedCSSRules($editable[0]);
    }
    $editable.find('*').each(function () {
        var $target = $(this);
        var css = getMatchedCSSRules(this);
        var style = $target.attr('style') || '';
        _.each(css, function (v,k) {
            if (!(new RegExp('(^|;)\s*' + k).test(style))) {
                style = k+':'+v+';'+style;
            }
        });
        if (_.isEmpty(style)) {
            $target.removeAttr('style');
        } else {
            $target.attr('style', style);
        }
    });
}

/**
 * Removes the inline style which is not necessary (because, for example, a
 * class on an element will induce the same style).
 *
 * @param {jQuery} $editable
 */
function styleToClass($editable) {
    getMatchedCSSRules($editable[0]);

    var $c = $('<span/>').appendTo(document.body);

    $editable.find('*').each(function () {
        var $target = $(this);
        var css = getMatchedCSSRules(this);
        var style = '';
        _.each(css, function (v,k) {
            if (!(new RegExp('(^|;)\s*' + k).test(style))) {
                style = k+':'+v+';'+style;
            }
        });
        css = ($c.attr('style', style).attr('style') || '').split(/\s*;\s*/);
        style = $target.attr('style') || '';
        _.each(css, function (v) {
            style = style.replace(v, '');
        });
        style = style.replace(/;+(\s;)*/g, ';').replace(/^;/g, '');
        if (style !== '') {
            $target.attr('style', style);
        } else {
            $target.removeAttr('style');
        }
    });
    $c.remove();
}

return {
    fontToImg: fontToImg,
    imgToFont: imgToFont,
    classToStyle: classToStyle,
    styleToClass: styleToClass,
};
});
