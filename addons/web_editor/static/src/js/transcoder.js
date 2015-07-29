odoo.define('web_editor.transcoder', function (require) {
'use strict';

var widget = require('web_editor.widget');

var cache = {};
var rulesCache = [];
var getMatchedCSSRules = function (a) {
    if(cache[a.tagName + "." +a.className]) {
        return cache[a.tagName + "." +a.className];
    }
    if (!rulesCache.length) {
        var sheets = document.styleSheets;
        for(var i = sheets.length-1; i >= 0 ; i--) {
            var rules = sheets[i].rules || sheets[i].cssRules;
            if (rules) {
                for(var r = rules.length-1; r >= 0; r--) {
                    var selectorText = rules[r].selectorText;
                    if (selectorText &&
                            rules[r].cssText &&
                            selectorText.indexOf(".") !== -1 &&
                            selectorText.indexOf(".note-") === -1 &&

                            selectorText.indexOf(":hover") === -1 &&
                            selectorText.indexOf(":before") === -1 &&
                            selectorText.indexOf(":after") === -1 &&
                            selectorText.indexOf(":active") === -1 &&
                            selectorText.indexOf(":link") === -1 &&
                            selectorText.indexOf("::") === -1) {
                        var st = selectorText.split(/\s*,\s*/);
                        for (var k=0; k<st.length; k++) {
                            rulesCache.push({ 'selector': st[k], 'style': rules[r].style });
                        }
                    }
                }
            }
        }
        rulesCache.reverse();
    }

    var css = [];
    a.matches = a.matches || a.webkitMatchesSelector || a.mozMatchesSelector || a.msMatchesSelector || a.oMatchesSelector;
    for(var r = 0; r < rulesCache.length; r++) {
        if (a.matches(rulesCache[r].selector)) {
            var style = rulesCache[r].style;
            if (style.parentRule) {
                var style_obj = {};
                for (var k=0, len=style.length; k<len; k++) {
                    style_obj[style[k]] = style[style[k].replace(/-(.)/g, function (a, b) { return b.toUpperCase(); })];
                }
                rulesCache[r].style = style = style_obj;
            }
            css.push([rulesCache[r].selector, style]);
        }
    }

    function specificity (selector) {
        // http://www.w3.org/TR/css3-selectors/#specificity
        var a = 0;
        selector.replace(/#[a-z0-9_-]+/gi, function () { a++; return ""; });
        var b = 0;
        selector.replace(/(\.[a-z0-9_-]+)|(\[.*?\])/gi, function () { b++; return ""; });
        var c = 0;
        selector.replace(/(\s+|:+)[a-z0-9_-]+/gi, function (a) { if(a.indexOf(':not(')===-1) c++; return ""; });
        return a*100 + b*10 + c;
    }
    css.sort(function (a, b) { return specificity(a[0]) - specificity(b[0]); });

    var style = {};
    _.each(css, function (v,k) {
        _.each(v[1], function (v,k) {
            if (!style[k] || style[k].indexOf('important') === -1 || v.indexOf('important') !== -1) {
                style[k] = v;
            }
        });
    });
    return cache[a.tagName + "." +a.className] = style;
};

// convert font awsome into image
var font_to_img = function ($editable) {
    $(".fa", $editable).each(function () {
        var $font = $(this);
        var content;
        _.find(widget.fontIcons, function (font) {
            return _.find(widget.getCssSelectors(font.parser), function (css) {
                if ($font.is(css[0].replace(/::?before$/, ''))) {
                    content = css[1].match(/content:\s*['"]?(.)['"]?/)[1];
                    return true;
                }
            });
        });
        if (content) {
            var size = parseInt(parseFloat($font.css("font-size"))/parseFloat($font.parent().css("font-size")),10);
            var color = $font.css("color").replace(/\s/g, '');
            var src = _.str.sprintf('/web_editor/font_to_img/%s/%s/'+$font.width(), window.encodeURI(content), window.encodeURI(color));
            var style = $font.attr("style");
            style = (style ? style.replace(/\s/g, '').replace(/(^|;)height:[^;]*/, '$1').replace(/(^|;)font-size:[^;]*/, '$1') : "") + "height:"+size+"em;";
            var $img = $("<img/>").attr("src", src).attr("data-class", $font.attr("class")).attr("style", style);
            $font.replaceWith($img);
        } else {
            $font.remove();
        }
    });
};
// convert image into font awsome
var img_to_font = function ($editable) {
    $("img[src*='/web_editor/font_to_img/']", $editable).each(function () {
        var $img = $(this);
        var $font = $("<span/>").attr("class", $img.data("class")).attr("style", $img.attr("style")).css("height", "");
        $img.replaceWith($font);
    });
};

// convert class into inline style to send by mail
var class_to_style = function ($editable) {
    if (!rulesCache.length) {
        getMatchedCSSRules($editable[0]);
    }
    var selector = _.map(rulesCache, function (a) { return a.selector;}).join(",");
    $editable.find(selector).each(function () {
        var $target = $(this);
        var css = getMatchedCSSRules(this);
        var style = $target.attr("style") || "";
        _.each(css, function (v,k) {
            if (style.indexOf(k) === -1) {
                style = k+":"+v+";"+style;
            }
        });
        $target.attr("style", style);
    });
};
// convert style into inline class from mail
var style_to_class = function ($editable) {
    getMatchedCSSRules($editable[0]);
    var classes = [];
    $editable.find("[class]").each(function () {
        classes = classes.concat(this.className.split(/\s+/));
    });

    var maybe_selector = _.filter(rulesCache, function (a) { return !!_.find(classes, function (b) { return a.selector.indexOf("."+b) !== -1; } ); });
    var selector = _.map(maybe_selector, function (a) { return a.selector;}).join(",");

    var $c = $('<span/>').appendTo("body");

    $editable.find(selector).each(function () {
        var $target = $(this);
        var css = getMatchedCSSRules(this);
        var style = "";
        _.each(css, function (v,k) {
            if (style.indexOf(k) === -1) {
                style = k+":"+v+";"+style;
            }
        });
        css = $c.attr("style", style).attr("style").split(/\s*;\s*/);
        style = $target.attr("style") || "";
        _.each(css, function (v) {
            style = style.replace(v, '');
        });
        $target.attr("style", style.replace(/;+(\s;)*/g, ';').replace(/^;/g, ''));
    });
    $c.remove();
};

return {
    'font_to_img': font_to_img,
    'img_to_font': img_to_font,
    'class_to_style': class_to_style,
    'style_to_class': style_to_class,
};

});