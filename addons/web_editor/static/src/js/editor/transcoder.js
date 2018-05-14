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
            // try...catch because browser may not able to enumerate rules for cross-domain sheets
            try {
                rules = sheets[i].rules || sheets[i].cssRules;
            } catch (e) {
                console.warn("Can't read the css rules of: " + sheets[i].href, e);
                continue;
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

    // The css generates all the attributes separately and not in simplified form.
    // In order to have a better compatibility (outlook for example) we simplify the css tags.
    // e.g. border-left-style: none; border-bottom-s .... will be simplified in border-style = none
    _.each([['margin'], ['padding'], ['border', 'style']], function (attr) {
        var p = attr[0];
        var e = attr[1] ? '-' + attr[1] : '';

        if (style[p+'-top'+e] || style[p+'-right'+e] || style[p+'-bottom'+e] || style[p+'-left'+e]) {
            if (style[p+'-top'+e] === style[p+'-right'+e] && style[p+'-top'+e] === style[p+'-bottom'+e] && style[p+'-top'+e] === style[p+'-left'+e]) {
                // keep => property: [top/right/bottom/left value];
                style[p+e] = style[p+'-top'+e];
            }
            else {
                // keep => property: [top value] [right value] [bottom value] [left value];
                style[p+e] = (style[p+'-top'+e] || 0) + ' ' + (style[p+'-right'+e] || 0) + ' ' + (style[p+'-bottom'+e] || 0) + ' ' + (style[p+'-left'+e] || 0);
                if (style[p+e].indexOf('inherit') !== -1 || style[p+e].indexOf('initial') !== -1) {
                    // keep => property-top: [top value]; property-right: [right value]; property-bottom: [bottom value]; property-left: [left value];
                    delete style[p+e];
                    return;
                }
            }
            delete style[p+'-top'+e];
            delete style[p+'-right'+e];
            delete style[p+'-bottom'+e];
            delete style[p+'-left'+e];
        }
    });

    if (style['border-bottom-left-radius']) {
        style['border-radius'] = style['border-bottom-left-radius'];
        delete style['border-bottom-left-radius'];
        delete style['border-bottom-right-radius'];
        delete style['border-top-left-radius'];
        delete style['border-top-right-radius'];
    }

    // if the border styling is initial we remove it to simplify the css tags for compatibility.
    // Also, since we do not send a css style tag, the initial value of the border is useless.
    _.each(_.keys(style), function (k) {
        if (k.indexOf('border') !== -1 && style[k] === 'initial') {
            delete style[k];
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

    // text-align inheritance does not seem to get past <td> elements on some
    // mail clients
    if (style['text-align'] === 'inherit') {
        var $el = $(a).parent();
        do {
            var align = $el.css('text-align');
            if (_.indexOf(['left', 'right', 'center', 'justify'], align) >= 0) {
                style['text-align'] = align;
                break;
            }
            $el = $el.parent();
        } while (!$el.is('html'));
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

/*
 * Utility function to apply function over descendants elements
 *
 * This is needed until the following issue of jQuery is solved:
 *  https://github.com./jquery/sizzle/issues/403
 *
 * @param {Element} node The root Element node
 * @param {Function} func The function applied over descendants
 */
function applyOverDescendants(node, func) {
    node = node.firstChild;
    while (node) {
        if (node.nodeType === 1) {
            func(node);
            applyOverDescendants(node, func);
        }
        node = node.nextSibling;
    }
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
    applyOverDescendants($editable[0], function (node) {
        var $target = $(node);
        var css = getMatchedCSSRules(node);
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
        // Apple Mail
        if (node.nodeName === 'TD' && !node.childNodes.length) {
            node.innerHTML = '&nbsp;';
        }

        // Outlook
        if (node.nodeName === 'A' && $target.hasClass('btn') && !$target.children().length) {
            var $hack = $('<table class="o_outlook_hack"><tr><td></td></tr></table>');
            $hack.find('td')
                .attr('height', $target.outerHeight())
                .css({
                    'margin': $target.css('padding'),
                    'border-radius': $target.css('border-radius'),
                    'background-color': $target.css('background-color'),
                });
            $target.after($hack);
            $target.appendTo($hack.find('td'));
            // the space add a line when it's a table but it's invisible when it's a link
            node = $hack[0].previousSibling;
            if (node && node.nodeType === Node.TEXT_NODE && !node.textContent.match(/\S/)) {
                $(node).remove();
            }
            node = $hack[0].nextSibling;
            if (node && node.nodeType === Node.TEXT_NODE && !node.textContent.match(/\S/)) {
                $(node).remove();
            }
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
    // Outlook revert
    $editable.find('table.o_outlook_hack').each(function () {
        $(this).after($('a', this));
    }).remove();

    getMatchedCSSRules($editable[0]);

    var $c = $('<span/>').appendTo(document.body);

    applyOverDescendants($editable[0], function (node) {
        var $target = $(node);
        var css = getMatchedCSSRules(node);
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

/**
 * Converts css display for attachment link to real image.
 * Without this post process, the display depends on the css and the picture
 * does not appear when we use the html without css (to send by email for e.g.)
 *
 * @param {jQuery} $editable
 */
function attachmentThumbnailToLinkImg($editable) {
    $editable.find('a[href*="/web/content/"][data-mimetype]:empty').each(function () {
        var $link = $(this);
        var $img = $('<img/>')
            .attr('src', $link.css('background-image').replace(/(^url\(['"])|(['"]\)$)/g, ''))
            .css('height', Math.max(1, $link.height()) + 'px')
            .css('width', Math.max(1, $link.width()) + 'px');
        $link.append($img);
    });
}

/**
 * Revert attachmentThumbnailToLinkImg changes
 *
 * @see attachmentThumbnailToLinkImg
 * @param {jQuery} $editable
 */
function linkImgToAttachmentThumbnail($editable) {
    $editable.find('a[href*="/web/content/"][data-mimetype] > img').remove();
}

return {
    fontToImg: fontToImg,
    imgToFont: imgToFont,
    classToStyle: classToStyle,
    styleToClass: styleToClass,
    attachmentThumbnailToLinkImg: attachmentThumbnailToLinkImg,
    linkImgToAttachmentThumbnail: linkImgToAttachmentThumbnail,
};
});
