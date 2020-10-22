odoo.define('web_editor.rte.summernote', function (require) {
'use strict';

var Class = require('web.Class');
const concurrency = require('web.concurrency');
var core = require('web.core');
// Use the top window's core.bus for dialog events so that they take the whole window
// instead of being confined to an iframe. This means that the event triggered on
// the bus by summernote in an iframe will be caught by the wysiwyg's SummernoteManager
// outside the iframe.
const topBus = window.top.odoo.__DEBUG__.services['web.core'].bus;
const {ColorpickerWidget} = require('web.Colorpicker');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
var mixins = require('web.mixins');
var fonts = require('wysiwyg.fonts');
var rte = require('web_editor.rte');
var ServicesMixin = require('web.ServicesMixin');
var weWidgets = require('wysiwyg.widgets');

var _t = core._t;

// Summernote Lib (neek change to make accessible: method and object)
var dom = $.summernote.core.dom;
var range = $.summernote.core.range;
var eventHandler = $.summernote.eventHandler;
var renderer = $.summernote.renderer;

var tplButton = renderer.getTemplate().button;
var tplIconButton = renderer.getTemplate().iconButton;
var tplDropdown = renderer.getTemplate().dropdown;

const processAndApplyColor = function (target, eventName, color, preview) {
    if (!color) {
        color = 'inherit';
    } else if (!ColorpickerWidget.isCSSColor(color)) {
        color = (eventName === "foreColor" ? 'text-' : 'bg-') + color;
    }
    var layoutInfo = dom.makeLayoutInfo(target);
    $.summernote.pluginEvents[eventName](undefined, eventHandler.modules.editor, layoutInfo, color, preview);
};
// Update and change the popovers content, and add history button
renderer.createPalette = function ($container, options) {
    const $dropdownContent = $container.find(".colorPalette");
    // The editor's root widget can be website or web's root widget and cannot be properly retrieved...
    const parent = odoo.__DEBUG__.services['root.widget'];
    _.each($dropdownContent, elem => {
        const eventName = elem.dataset.eventName;
        let colorpicker = null;
        const mutex = new concurrency.MutexedDropPrevious();
        const $dropdown = $(elem).closest('.btn-group, .dropdown');
        let manualOpening = false;
        // Prevent dropdown closing on colorpicker click
        $dropdown.on('hide.bs.dropdown', ev => {
            return !(ev.clickEvent && ev.clickEvent.originalEvent && ev.clickEvent.originalEvent.__isColorpickerClick);
        });
        $dropdown.on('show.bs.dropdown', () => {
            if (manualOpening) {
                return true;
            }
            mutex.exec(() => {
                const oldColorpicker = colorpicker;
                const hookEl = oldColorpicker ? oldColorpicker.el : elem;

                const r = range.create();
                const targetNode = r.sc;
                const targetElement = targetNode.nodeType === Node.ELEMENT_NODE ? targetNode : targetNode.parentNode;
                colorpicker = new ColorPaletteWidget(parent, {
                    excluded: ['transparent_grayscale'],
                    $editable: rte.Class.prototype.editable(), // Our parent is the root widget, we can't retrieve the editable section from it...
                    selectedColor: $(targetElement).css(eventName === "foreColor" ? 'color' : 'backgroundColor'),
                });
                colorpicker.on('custom_color_picked color_picked', null, ev => {
                    processAndApplyColor(ev.data.target, eventName, ev.data.color);
                });
                colorpicker.on('color_hover color_leave', null, ev => {
                    processAndApplyColor(ev.data.target, eventName, ev.data.color, true);
                });
                colorpicker.on('enter_key_color_colorpicker', null, () => {
                    $dropdown.children('.dropdown-toggle').dropdown('hide');
                });
                return colorpicker.replace(hookEl).then(() => {
                    if (oldColorpicker) {
                        oldColorpicker.destroy();
                    }
                    manualOpening = true;
                    $dropdown.children('.dropdown-toggle').dropdown('show');
                    manualOpening = false;
                });
            });
            return false;
        });
    });
};

var fn_tplPopovers = renderer.tplPopovers;
renderer.tplPopovers = function (lang, options) {
    var $popover = $(fn_tplPopovers.call(this, lang, options));

    var $imagePopover = $popover.find('.note-image-popover');
    var $linkPopover = $popover.find('.note-link-popover');
    var $airPopover = $popover.find('.note-air-popover');

    //////////////// image popover

    // add center button for images
    $(tplIconButton('fa fa-align-center', {
        title: _t('Center'),
        event: 'floatMe',
        value: 'center'
    })).insertAfter($imagePopover.find('[data-event="floatMe"][data-value="left"]'));
    $imagePopover.find('button[data-event="removeMedia"]').parent().remove();
    $imagePopover.find('button[data-event="floatMe"][data-value="none"]').remove();

    // padding button
    var $padding = $('<div class="btn-group"/>');
    $padding.insertBefore($imagePopover.find('.btn-group:first'));
    var dropdown_content = [
        '<li><a class="dropdown-item" data-event="padding" href="#" data-value="">'+_t('None')+'</a></li>',
        '<li><a class="dropdown-item" data-event="padding" href="#" data-value="small">'+_t('Small')+'</a></li>',
        '<li><a class="dropdown-item" data-event="padding" href="#" data-value="medium">'+_t('Medium')+'</a></li>',
        '<li><a class="dropdown-item" data-event="padding" href="#" data-value="large">'+_t('Large')+'</a></li>',
        '<li><a class="dropdown-item" data-event="padding" href="#" data-value="xl">'+_t('Xl')+'</a></li>',
    ];
    $(tplIconButton('fa fa-plus-square-o', {
        title: _t('Padding'),
        dropdown: tplDropdown(dropdown_content)
    })).appendTo($padding);

    // circle, boxed... options became toggled
    $imagePopover.find('[data-event="imageShape"]:not([data-value])').remove();
    var $button = $(tplIconButton('fa fa-sun-o', {
        title: _t('Shadow'),
        event: 'imageShape',
        value: 'shadow'
    })).insertAfter($imagePopover.find('[data-event="imageShape"][data-value="rounded-circle"]'));

    // add spin for fa
    var $spin = $('<div class="btn-group d-none only_fa"/>').insertAfter($button.parent());
    $(tplIconButton('fa fa-refresh', {
            title: _t('Spin'),
            event: 'imageShape',
            value: 'fa-spin'
        })).appendTo($spin);

    // resize for fa
    var $resizefa = $('<div class="btn-group d-none only_fa"/>')
        .insertAfter($imagePopover.find('.btn-group:has([data-event="resize"])'));
    for (var size=1; size<=5; size++) {
        $(tplButton('<span class="note-fontsize-10">'+size+'x</span>', {
          title: size+"x",
          event: 'resizefa',
          value: size+''
        })).appendTo($resizefa);
    }
    var $colorfa = $airPopover.find('.note-color').clone();
    $colorfa.find(".dropdown-menu").css('min-width', '172px');
    $resizefa.after($colorfa);

    // show dialog box and delete
    var $imageprop = $('<div class="btn-group"/>');
    $imageprop.appendTo($imagePopover.find('.popover-body'));
    $(tplIconButton('fa fa-file-image-o', {
            title: _t('Edit'),
            event: 'showImageDialog'
        })).appendTo($imageprop);
    $(tplIconButton('fa fa-trash-o', {
            title: _t('Remove'),
            event: 'delete'
        })).appendTo($imageprop);

    $(tplIconButton('fa fa-crop', {
        title: _t('Crop Image'),
        event: 'cropImage',
    })).insertAfter($imagePopover.find('[data-event="imageShape"][data-value="img-thumbnail"]'));

    $imagePopover.find('.popover-body').append($airPopover.find(".note-history").clone());

    $imagePopover.find('[data-event="showImageDialog"]').before($airPopover.find('[data-event="showLinkDialog"]').clone());

    var $alt = $('<div class="btn-group"/>');
    $alt.appendTo($imagePopover.find('.popover-body'));
    $alt.append('<button class="btn btn-secondary" data-event="alt"><strong>' + _t('Description') + ': </strong><span class="o_image_alt"/></button>');

    //////////////// link popover

    $linkPopover.find('.popover-body').append($airPopover.find(".note-history").clone());

    $linkPopover.find('button[data-event="showLinkDialog"] i').attr("class", "fa fa-link");
    $linkPopover.find('button[data-event="unlink"]').before($airPopover.find('button[data-event="showImageDialog"]').clone());

    //////////////// text/air popover

    //// highlight the text format
    $airPopover.find('.note-style .dropdown-toggle').on('mousedown', function () {
        var $format = $airPopover.find('[data-event="formatBlock"]');
        var node = range.create().sc;
        var formats = $format.map(function () { return $(this).data("value"); }).get();
        while (node && (!node.tagName || (!node.tagName || formats.indexOf(node.tagName.toLowerCase()) === -1))) {
            node = node.parentNode;
        }
        $format.removeClass('active');
        $format.filter('[data-value="'+(node ? node.tagName.toLowerCase() : "p")+'"]')
            .addClass("active");
    });

    //////////////// tooltip

    setTimeout(function () {
        $airPopover.add($linkPopover).add($imagePopover).find("button")
            .tooltip('dispose')
            .tooltip({
                container: 'body',
                trigger: 'hover',
                placement: 'bottom'
            }).on('click', function () {$(this).tooltip('hide');});
    });

    return $popover;
};

var fn_boutton_update = eventHandler.modules.popover.button.update;
eventHandler.modules.popover.button.update = function ($container, oStyle) {
    // stop animation when edit content
    var previous = $(".note-control-selection").data('target');
    if (previous) {
        var $previous = $(previous);
        $previous.css({"-webkit-animation-play-state": "", "animation-play-state": "", "-webkit-transition": "", "transition": "", "-webkit-animation": "", "animation": ""});
        $previous.find('.o_we_selected_image').addBack('.o_we_selected_image').removeClass('o_we_selected_image');
    }
    // end

    fn_boutton_update.call(this, $container, oStyle);

    $container.find('.note-color').removeClass('d-none');

    if (oStyle.image) {
        $container.find('[data-event]').removeClass("active");

        $container.find('a[data-event="padding"][data-value="small"]').toggleClass("active", $(oStyle.image).hasClass("padding-small"));
        $container.find('a[data-event="padding"][data-value="medium"]').toggleClass("active", $(oStyle.image).hasClass("padding-medium"));
        $container.find('a[data-event="padding"][data-value="large"]').toggleClass("active", $(oStyle.image).hasClass("padding-large"));
        $container.find('a[data-event="padding"][data-value="xl"]').toggleClass("active", $(oStyle.image).hasClass("padding-xl"));
        $container.find('a[data-event="padding"][data-value=""]').toggleClass("active", !$container.find('li a.active[data-event="padding"]').length);

        $(oStyle.image).addClass('o_we_selected_image');

        if (dom.isImgFont(oStyle.image)) {
            $container.find('.note-fore-color-preview > button > .caret').css('border-bottom-color', $(oStyle.image).css('color'));
            $container.find('.note-back-color-preview > button > .caret').css('border-bottom-color', $(oStyle.image).css('background-color'));

            $container.find('.btn-group:not(.only_fa):has(button[data-event="resize"],button[data-value="img-thumbnail"])').addClass('d-none');
            $container.find('.only_fa').removeClass('d-none');
            $container.find('button[data-event="resizefa"][data-value="2"]').toggleClass("active", $(oStyle.image).hasClass("fa-2x"));
            $container.find('button[data-event="resizefa"][data-value="3"]').toggleClass("active", $(oStyle.image).hasClass("fa-3x"));
            $container.find('button[data-event="resizefa"][data-value="4"]').toggleClass("active", $(oStyle.image).hasClass("fa-4x"));
            $container.find('button[data-event="resizefa"][data-value="5"]').toggleClass("active", $(oStyle.image).hasClass("fa-5x"));
            $container.find('button[data-event="resizefa"][data-value="1"]').toggleClass("active", !$container.find('.active[data-event="resizefa"]').length);

            $container.find('button[data-event="imageShape"][data-value="fa-spin"]').toggleClass("active", $(oStyle.image).hasClass("fa-spin"));
            $container.find('button[data-event="imageShape"][data-value="shadow"]').toggleClass("active", $(oStyle.image).hasClass("shadow"));
            $container.find('.btn-group:has(button[data-event="imageShape"])').removeClass("d-none");

        } else {
            $container.find('.d-none:not(.only_fa, .note-recent-color)').removeClass('d-none');
            $container.find('.only_fa').addClass('d-none');
            var width = ($(oStyle.image).attr('style') || '').match(/(^|;|\s)width:\s*([0-9]+%)/);
            if (width) {
                width = width[2];
            }
            $container.find('button[data-event="resize"][data-value="auto"]').toggleClass("active", width !== "100%" && width !== "50%" && width !== "25%");
            $container.find('button[data-event="resize"][data-value="1"]').toggleClass("active", width === "100%");
            $container.find('button[data-event="resize"][data-value="0.5"]').toggleClass("active", width === "50%");
            $container.find('button[data-event="resize"][data-value="0.25"]').toggleClass("active", width === "25%");

            $container.find('button[data-event="imageShape"][data-value="shadow"]').toggleClass("active", $(oStyle.image).hasClass("shadow"));

            if (!$(oStyle.image).is("img")) {
                $container.find('.btn-group:has(button[data-event="imageShape"])').addClass('d-none');
            }

            $container.find('.note-color').addClass('d-none');
        }

        $container.find('button[data-event="floatMe"][data-value="left"]').toggleClass("active", $(oStyle.image).hasClass("float-left"));
        $container.find('button[data-event="floatMe"][data-value="center"]').toggleClass("active", $(oStyle.image).hasClass("d-block mx-auto"));
        $container.find('button[data-event="floatMe"][data-value="right"]').toggleClass("active", $(oStyle.image).hasClass("float-right"));

        $(oStyle.image).trigger('attributes_change');
    } else {
        $container.find('.note-fore-color-preview > button > .caret').css('border-bottom-color', oStyle.color);
        $container.find('.note-back-color-preview > button > .caret').css('border-bottom-color', oStyle['background-color']);
    }
};

var fn_toolbar_boutton_update = eventHandler.modules.toolbar.button.update;
eventHandler.modules.toolbar.button.update = function ($container, oStyle) {
    fn_toolbar_boutton_update.call(this, $container, oStyle);

    $container.find('button[data-event="insertUnorderedList"]').toggleClass("active", $(oStyle.ancestors).is('ul:not(.o_checklist)'));
    $container.find('button[data-event="insertOrderedList"]').toggleClass("active", $(oStyle.ancestors).is('ol'));
    $container.find('button[data-event="insertCheckList"]').toggleClass("active", $(oStyle.ancestors).is('ul.o_checklist'));
};

var fn_popover_update = eventHandler.modules.popover.update;
eventHandler.modules.popover.update = function ($popover, oStyle, isAirMode) {
    var $imagePopover = $popover.find('.note-image-popover');
    var $linkPopover = $popover.find('.note-link-popover');
    var $airPopover = $popover.find('.note-air-popover');

    fn_popover_update.call(this, $popover, oStyle, isAirMode);

    if (oStyle.image) {
        if (oStyle.image.parentNode.className.match(/(^|\s)media_iframe_video(\s|$)/i)) {
            oStyle.image = oStyle.image.parentNode;
        }
        var alt =  $(oStyle.image).attr("alt");

        $imagePopover.find('.o_image_alt').text( (alt || "").replace(/&quot;/g, '"') ).parent().toggle(oStyle.image.tagName === "IMG");
        $imagePopover.show();

        // for video tag (non-void) we select the range over the tag,
        // for other media types we get the first descendant leaf element
        var target_node = oStyle.image;
        if (!oStyle.image.className.match(/(^|\s)media_iframe_video(\s|$)/i)) {
            target_node = dom.firstChild(target_node);
        }
        range.createFromNode(target_node).select();
        // save range on the editor so it is not lost if restored
        eventHandler.modules.editor.saveRange(dom.makeLayoutInfo(target_node).editable());
    } else {
        $(".note-control-selection").hide();
    }

    if (oStyle.image || (oStyle.range && (!oStyle.range.isCollapsed() || (oStyle.range.sc.tagName && !dom.isAnchor(oStyle.range.sc)))) || (oStyle.image && !$(oStyle.image).closest('a').length)) {
        $linkPopover.hide();
        oStyle.anchor = false;
    }

    if (oStyle.image || oStyle.anchor || (oStyle.range && !$(oStyle.range.sc).closest('.note-editable').length)) {
        $airPopover.hide();
    } else {
        $airPopover.show();
    }

    const $externalHistoryButtons = $('.o_we_external_history_buttons');
    if ($externalHistoryButtons.length) {
        const $noteHistory = $('.note-history');
        $noteHistory.addClass('d-none');
        $externalHistoryButtons.find(':first-child').prop('disabled', $noteHistory.find('[data-event=undo]').prop('disabled'));
        $externalHistoryButtons.find(':last-child').prop('disabled', $noteHistory.find('[data-event=redo]').prop('disabled'));
    }
    $popover.trigger('summernote_popover_update_call');
};

var fn_handle_update = eventHandler.modules.handle.update;
eventHandler.modules.handle.update = function ($handle, oStyle, isAirMode) {
    fn_handle_update.call(this, $handle, oStyle, isAirMode);
    if (oStyle.image) {
        $handle.find('.note-control-selection').hide();
    }
};

// Hack for image and link editor
function getImgTarget($editable) {
    var $handle = $editable ? dom.makeLayoutInfo($editable).handle() : undefined;
    return $(".note-control-selection", $handle).data('target');
}
eventHandler.modules.editor.padding = function ($editable, sValue) {
    var $target = $(getImgTarget($editable));
    var paddings = "small medium large xl".split(/\s+/);
    $editable.data('NoteHistory').recordUndo();
    if (sValue.length) {
        paddings.splice(paddings.indexOf(sValue),1);
        $target.toggleClass('padding-'+sValue);
    }
    $target.removeClass("padding-" + paddings.join(" padding-"));
};
eventHandler.modules.editor.resize = function ($editable, sValue) {
    var $target = $(getImgTarget($editable));
    $editable.data('NoteHistory').recordUndo();
    var width = ($target.attr('style') || '').match(/(^|;|\s)width:\s*([0-9]+)%/);
    if (width) {
        width = width[2]/100;
    }
    $target.css('width', (width !== sValue && sValue !== "auto") ? (sValue * 100) + '%' : '');
};
eventHandler.modules.editor.resizefa = function ($editable, sValue) {
    var $target = $(getImgTarget($editable));
    $editable.data('NoteHistory').recordUndo();
    $target.attr('class', $target.attr('class').replace(/\s*fa-[0-9]+x/g, ''));
    if (+sValue > 1) {
        $target.addClass('fa-'+sValue+'x');
    }
};
eventHandler.modules.editor.floatMe = function ($editable, sValue) {
    var $target = $(getImgTarget($editable));
    $editable.data('NoteHistory').recordUndo();
    switch (sValue) {
        case 'center': $target.toggleClass('d-block mx-auto').removeClass('float-right float-left'); break;
        case 'left': $target.toggleClass('float-left').removeClass('float-right d-block mx-auto'); break;
        case 'right': $target.toggleClass('float-right').removeClass('float-left d-block mx-auto'); break;
    }
};
eventHandler.modules.editor.imageShape = function ($editable, sValue) {
    var $target = $(getImgTarget($editable));
    $editable.data('NoteHistory').recordUndo();
    $target.toggleClass(sValue);
};

eventHandler.modules.linkDialog.showLinkDialog = function ($editable, $dialog, linkInfo) {
    $editable.data('range').select();
    $editable.data('NoteHistory').recordUndo();

    var commonAncestor = linkInfo.range.commonAncestor();
    if (commonAncestor && commonAncestor.closest) {
        var link = commonAncestor.closest('a');
        linkInfo.className = link && link.className;
    }

    var def = new $.Deferred();
    topBus.trigger('link_dialog_demand', {
        $editable: $editable,
        linkInfo: linkInfo,
        onSave: function (linkInfo) {
            linkInfo.range.select();
            $editable.data('range', linkInfo.range);
            def.resolve(linkInfo);
            $editable.trigger('keyup');
            $('.note-popover .note-link-popover').show();
        },
        onCancel: def.reject.bind(def),
    });
    return def;
};
eventHandler.modules.imageDialog.showImageDialog = function ($editable) {
    var r = $editable.data('range');
    if (r.sc.tagName && r.sc.childNodes.length) {
        r.sc = r.sc.childNodes[r.so];
    }
    var media = $(r.sc).parents().addBack().filter(function (i, el) {
        return dom.isImg(el);
    })[0];
    var options = $editable.closest('.o_editable, .note-editor').data('options');
    topBus.trigger('media_dialog_demand', {
        $editable: $editable,
        media: media,
        options: {
            onUpload: $editable.data('callbacks').onUpload,
            noVideos: options && options.noVideos,
        },
        onSave: function (media) {
            if(media && !document.body.contains(media)) {
            r.insertNode(media);
            };
        },
    });
    return new $.Deferred().reject();
};
$.summernote.pluginEvents.alt = function (event, editor, layoutInfo, sorted) {
    var $editable = layoutInfo.editable();
    var $selection = layoutInfo.handle().find('.note-control-selection');
    topBus.trigger('alt_dialog_demand', {
        $editable: $editable,
        media: $selection.data('target'),
    });
};
$.summernote.pluginEvents.cropImage = function (event, editor, layoutInfo, sorted) {
    var $editable = layoutInfo.editable();
    var $selection = layoutInfo.handle().find('.note-control-selection');
    topBus.trigger('crop_image_demand', {
        $editable: $editable,
        media: $selection.data('target'),
    });
};

// Utils
var fn_is_void = dom.isVoid || function () {};
dom.isVoid = function (node) {
    return fn_is_void(node) || dom.isImgFont(node) || (node && node.className && node.className.match(/(^|\s)media_iframe_video(\s|$)/i));
};
var fn_is_img = dom.isImg || function () {};
dom.isImg = function (node) {
    return fn_is_img(node) || dom.isImgFont(node) || (node && (node.nodeName === "IMG" || (node.className && node.className.match(/(^|\s)(media_iframe_video|o_image)(\s|$)/i)) ));
};
var fn_is_forbidden_node = dom.isForbiddenNode || function () {};
dom.isForbiddenNode = function (node) {
    if (node.tagName === "BR") {
        return false;
    }
    return fn_is_forbidden_node(node) || $(node).is(".media_iframe_video");
};
var fn_is_img_font = dom.isImgFont || function () {};
dom.isImgFont = function (node) {
    if (fn_is_img_font(node)) return true;

    var nodeName = node && node.nodeName.toUpperCase();
    var className = (node && node.className || "");
    if (node && (nodeName === "SPAN" || nodeName === "I") && className.length) {
        var classNames = className.split(/\s+/);
        for (var k=0; k<fonts.fontIcons.length; k++) {
            if (_.intersection(fonts.fontIcons[k].alias, classNames).length) {
                return true;
            }
        }
    }
    return false;
};
var fn_is_font = dom.isFont; // re-overwrite font to include theme icons
dom.isFont = function (node) {
    return fn_is_font(node) || dom.isImgFont(node);
};

var fn_visible = $.summernote.pluginEvents.visible;
$.summernote.pluginEvents.visible = function (event, editor, layoutInfo) {
    var res = fn_visible.apply(this, arguments);
    var rng = range.create();
    if (!rng) return res;
    var $node = $(dom.node(rng.sc));
    if (($node.is('[data-oe-type="html"]') || $node.is('[data-oe-field="arch"]')) &&
        $node.hasClass("o_editable") &&
        !$node[0].children.length &&
        "h1 h2 h3 h4 h5 h6 p b bold i u code sup strong small pre th td span label".toUpperCase().indexOf($node[0].nodeName) === -1) {
        var p = $('<p><br/></p>')[0];
        $node.append( p );
        range.createFromNode(p.firstChild).select();
    }
    return res;
};

function prettify_html(html) {
    html = html.trim();
    var result = '',
        level = 0,
        get_space = function (level) {
            var i = level, space = '';
            while (i--) space += '  ';
            return space;
        },
        reg = /^<\/?(a|span|font|u|em|i|strong|b)(\s|>)/i,
        inline_level = Infinity,
        tokens = _.compact(_.flatten(_.map(html.split(/</), function (value) {
            value = value.replace(/\s+/g, ' ').split(/>/);
            value[0] = /\S/.test(value[0]) ? '<' + value[0] + '>' : '';
            return value;
        })));

    // reduce => merge inline style + text

    for (var i = 0, l = tokens.length; i < l; i++) {
        var token = tokens[i];
        var inline_tag = reg.test(token);
        var inline = inline_tag || inline_level <= level;

        if (token[0] === '<' && token[1] === '/') {
            if (inline_tag && inline_level === level) {
                inline_level = Infinity;
            }
            level--;
        }

        if (!inline && !/\S/.test(token)) {
            continue;
        }
        if (!inline || (token[1] !== '/' && inline_level > level)) {
            result += get_space(level);
        }

        if (token[0] === '<' && token[1] !== '/') {
            level++;
            if (inline_tag && inline_level > level) {
                inline_level = level;
            }
        }

        if (token.match(/^<(img|hr|br)/)) {
            level--;
        }

        // don't trim inline content (which could change appearance)
        if (!inline) {
            token = token.trim();
        }

        result += token.replace(/\s+/, ' ');

        if (inline_level > level) {
            result += '\n';
        }
    }
    return result;
}

/*
 * This override when clicking on the 'Code View' button has two aims:
 *
 * - have our own code view implementation for FieldTextHtml
 * - add an 'enable' paramater to call the function directly and allow us to
 *   disable (false) or enable (true) the code view mode.
 */
$.summernote.pluginEvents.codeview = function (event, editor, layoutInfo, enable) {
    if (!layoutInfo) {
        return;
    }
    if (layoutInfo.toolbar) {
        // if editor inline (FieldTextHtmlSimple)
        var is_activated = $.summernote.eventHandler.modules.codeview.isActivated(layoutInfo);
        if (is_activated === enable) {
            return;
        }
        return eventHandler.modules.codeview.toggle(layoutInfo);
    } else {
        // if editor iframe (FieldTextHtml)
        var $editor = layoutInfo.editor();
        var $textarea = $editor.prev('textarea');
        if ($textarea.is('textarea') === enable) {
            return;
        }

        if (!$textarea.length) {
            // init and create texarea
            var html = prettify_html($editor.prop("innerHTML"));
            $editor.parent().css({
                'position': 'absolute',
                'top': 0,
                'bottom': 0,
                'left': 0,
                'right': 0
            });
            $textarea = $('<textarea/>').css({
                'margin': '0 -4px',
                'padding': '0 4px',
                'border': 0,
                'top': '51px',
                'left': '620px',
                'width': '100%',
                'font-family': 'sans-serif',
                'font-size': '13px',
                'height': '98%',
                'white-space': 'pre',
                'word-wrap': 'normal'
            }).val(html).data('init', html);
            $editor.before($textarea);
            $editor.hide();
        } else {
            // save changes
            $editor.prop('innerHTML', $textarea.val().replace(/\s*\n\s*/g, '')).trigger('content_changed');
            $textarea.remove();
            $editor.show();
        }
    }
};

// Fix ie and re-range to don't break snippet
var last_div;
var last_div_change;
var last_editable;
var initial_data = {};
function reRangeSelectKey(event) {
    initial_data.range = null;
    if (event.shiftKey && event.keyCode >= 37 && event.keyCode <= 40 && !$(event.target).is("input, textarea, select")) {
        var r = range.create();
        if (r) {
            var rng = r.reRange(event.keyCode <= 38);
            if (r !== rng) {
                rng.select();
            }
        }
    }
}
function reRangeSelect(event, dx, dy) {
    var r = range.create();
    if (!r || r.isCollapsed()) return;

    // check if the user move the caret on up or down
    var data = r.reRange(dy < 0 || (dy === 0 && dx < 0));

    if (data.sc !== r.sc || data.so !== r.so || data.ec !== r.ec || data.eo !== r.eo) {
        setTimeout(function () {
            data.select();
            $(data.sc.parentNode).closest('.note-popover');
        },0);
    }

    $(data.sc).closest('.o_editable').data('range', r);
    return r;
}
function summernote_mouseup(event) {
    if ($(event.target).closest("#web_editor-top-navbar, .note-popover").length) {
        return;
    }
    // don't rerange if simple click
    if (initial_data.event) {
        var dx = event.clientX - (event.shiftKey && initial_data.rect ? initial_data.rect.left : initial_data.event.clientX);
        var dy = event.clientY - (event.shiftKey && initial_data.rect ? initial_data.rect.top : initial_data.event.clientY);
        if (10 < Math.pow(dx, 2)+Math.pow(dy, 2)) {
            reRangeSelect(event, dx, dy);
        }
    }

    if (!$(event.target).closest(".o_editable").length) {
        return;
    }
    if (!initial_data.range || !event.shiftKey) {
        setTimeout(function () {
            initial_data.range = range.create();
        },0);
    }
}
var remember_selection;
function summernote_mousedown(event) {
    rte.history.splitNext();

    var $editable = $(event.target).closest(".o_editable, .note-editor");
    var r;

    if (document.documentMode) {
        summernote_ie_fix(event, function (node) { return node.tagName === "DIV" || node.tagName === "IMG" || (node.dataset && node.dataset.oeModel); });
    } else if (last_div && event.target !== last_div) {
        if (last_div.tagName === "A") {
            summernote_ie_fix(event, function (node) { return node.dataset && node.dataset.oeModel; });
        } else if ($editable.length) {
            if (summernote_ie_fix(event, function (node) { return node.tagName === "A"; })) {
                r = range.create();
                r.select();
            }
        }
    }

    // restore range if range lost after clicking on non-editable area
    try {
        r = range.create();
    } catch (e) {
        // If this code is running inside an iframe-editor and that the range
        // is outside of this iframe, this will fail as the iframe does not have
        // the permission to check the outside content this way. In that case,
        // we simply ignore the exception as it is as if there was no range.
        return;
    }
    var editables = $(".o_editable[contenteditable], .note-editable[contenteditable]");
    var r_editable = editables.has((r||{}).sc).addBack(editables.filter((r||{}).sc));
    if (!r_editable.closest('.note-editor').is($editable) && !r_editable.filter('.o_editable').is(editables)) {
        var saved_editable = editables.has((remember_selection||{}).sc);
        if ($editable.length && !saved_editable.closest('.o_editable, .note-editor').is($editable)) {
            remember_selection = range.create(dom.firstChild($editable[0]), 0);
        } else if (!saved_editable.length) {
            remember_selection = undefined;
        }
        if (remember_selection) {
            try {
                remember_selection.select();
            } catch (e) {
                console.warn(e);
            }
        }
    } else if (r_editable.length) {
        remember_selection = r;
    }

    initial_data.event = event;

    // keep selection when click with shift
    if (event.shiftKey && $editable.length) {
        if (initial_data.range) {
            initial_data.range.select();
        }
        var rect = r && r.getClientRects();
        initial_data.rect = rect && rect.length ? rect[0] : { top: 0, left: 0 };
    }
}

function summernote_ie_fix(event, pred) {
    var editable;
    var div;
    var node = event.target;
    while (node.parentNode) {
        if (!div && pred(node)) {
            div = node;
        }
        if (last_div !== node && (node.getAttribute('contentEditable')==='false' || node.className && (node.className.indexOf('o_not_editable') !== -1))) {
            break;
        }
        if (node.className && node.className.indexOf('o_editable') !== -1) {
            if (!div) {
                div = node;
            }
            editable = node;
            break;
        }
        node = node.parentNode;
    }

    if (!editable) {
        $(last_div_change).removeAttr("contentEditable").removeProp("contentEditable");
        $(last_editable).attr("contentEditable", "true").prop("contentEditable", "true");
        last_div_change = null;
        last_editable = null;
        return;
    }

    if (div === last_div) {
        return;
    }

    last_div = div;

    $(last_div_change).removeAttr("contentEditable").removeProp("contentEditable");

    if (last_editable !== editable) {
        if ($(editable).is("[contentEditable='true']")) {
           $(editable).removeAttr("contentEditable").removeProp("contentEditable");
            last_editable = editable;
        } else {
            last_editable = null;
        }
    }
    if (!$(div).attr("contentEditable") && !$(div).is("[data-oe-type='many2one'], [data-oe-type='contact']")) {
        $(div).attr("contentEditable", "true").prop("contentEditable", "true");
        last_div_change = div;
    } else {
        last_div_change = null;
    }
    return editable !== div ? div : null;
}

var fn_attach = eventHandler.attach;
eventHandler.attach = function (oLayoutInfo, options) {
    fn_attach.call(this, oLayoutInfo, options);

    oLayoutInfo.editor().on('dragstart', 'img', function (e) { e.preventDefault(); });
    $(document).on('mousedown', summernote_mousedown).on('mouseup', summernote_mouseup);
    oLayoutInfo.editor().off('click').on('click', function (e) {e.preventDefault();}); // if the content editable is a link

    /**
     * Open Media Dialog on double click on an image/video/icon.
     * Shows a tooltip on click to say to the user he can double click.
     */
    create_dblclick_feature("img, .media_iframe_video, i.fa, span.fa, a.o_image", function () {
        eventHandler.modules.imageDialog.show(oLayoutInfo);
    });

    /**
     * Open Link Dialog on double click on a link/button.
     * Shows a tooltip on click to say to the user he can double click.
     */
    create_dblclick_feature("a[href], a.btn, button.btn", function () {
        eventHandler.modules.linkDialog.show(oLayoutInfo);
    });

    oLayoutInfo.editable().on('mousedown', function (e) {
        if (dom.isImg(e.target) && dom.isContentEditable(e.target)) {
            range.createFromNode(e.target).select();
        }
    });
    $(document).on("keyup", reRangeSelectKey);

    var clone_data = false;

    if (options.model) {
        oLayoutInfo.editable().data({'oe-model': options.model, 'oe-id': options.id});
    }
    if (options.getMediaDomain) {
        oLayoutInfo.editable().data('oe-media-domain', options.getMediaDomain);
    }

    var $node = oLayoutInfo.editor();
    if ($node.data('oe-model') || $node.data('oe-translation-id')) {
        $node.on('content_changed', function () {
            var $nodes = $('[data-oe-model], [data-oe-translation-id]')
                .filter(function () { return this !== $node[0];});

            if ($node.data('oe-model')) {
                $nodes = $nodes.filter('[data-oe-model="'+$node.data('oe-model')+'"]')
                    .filter('[data-oe-id="'+$node.data('oe-id')+'"]')
                    .filter('[data-oe-field="'+$node.data('oe-field')+'"]');
            }
            if ($node.data('oe-translation-id')) $nodes = $nodes.filter('[data-oe-translation-id="'+$node.data('oe-translation-id')+'"]');
            if ($node.data('oe-type')) $nodes = $nodes.filter('[data-oe-type="'+$node.data('oe-type')+'"]');
            if ($node.data('oe-expression')) $nodes = $nodes.filter('[data-oe-expression="'+$node.data('oe-expression')+'"]');
            if ($node.data('oe-xpath')) $nodes = $nodes.filter('[data-oe-xpath="'+$node.data('oe-xpath')+'"]');
            if ($node.data('oe-contact-options')) $nodes = $nodes.filter('[data-oe-contact-options="'+$node.data('oe-contact-options')+'"]');

            var nodes = $node.get();

            if ($node.data('oe-type') === "many2one") {
                $nodes = $nodes.add($('[data-oe-model]')
                    .filter(function () { return this !== $node[0] && nodes.indexOf(this) === -1; })
                    .filter('[data-oe-many2one-model="'+$node.data('oe-many2one-model')+'"]')
                    .filter('[data-oe-many2one-id="'+$node.data('oe-many2one-id')+'"]')
                    .filter('[data-oe-type="many2one"]'));

                $nodes = $nodes.add($('[data-oe-model]')
                    .filter(function () { return this !== $node[0] && nodes.indexOf(this) === -1; })
                    .filter('[data-oe-model="'+$node.data('oe-many2one-model')+'"]')
                    .filter('[data-oe-id="'+$node.data('oe-many2one-id')+'"]')
                    .filter('[data-oe-field="name"]'));
            }

            if (!clone_data) {
                clone_data = true;
                $nodes.html(this.innerHTML);
                clone_data = false;
            }
        });
    }

    var custom_toolbar = oLayoutInfo.toolbar ? oLayoutInfo.toolbar() : undefined;
    var $toolbar = $(oLayoutInfo.popover()).add(custom_toolbar);
    $('button[data-event="undo"], button[data-event="redo"]', $toolbar).attr('disabled', true);

    $(oLayoutInfo.editor())
        .add(oLayoutInfo.handle())
        .add(oLayoutInfo.popover())
        .add(custom_toolbar)
        .on('click content_changed', function () {
            $('button[data-event="undo"]', $toolbar).attr('disabled', !oLayoutInfo.editable().data('NoteHistory').hasUndo());
            $('button[data-event="redo"]', $toolbar).attr('disabled', !oLayoutInfo.editable().data('NoteHistory').hasRedo());
        });

    function create_dblclick_feature(selector, callback) {
        var show_tooltip = true;

        oLayoutInfo.editor().on("dblclick", selector, function (e) {
            var $target = $(e.target);
            if (!dom.isContentEditable($target)) {
                // Prevent edition of non editable parts
                return;
            }

            show_tooltip = false;
            callback();
            e.stopImmediatePropagation();
        });

        oLayoutInfo.editor().on("click", selector, function (e) {
            var $target = $(e.target);
            if (!dom.isContentEditable($target)) {
                // Prevent edition of non editable parts
                return;
            }

            show_tooltip = true;
            setTimeout(function () {
                // Do not show tooltip on double-click and if there is already one
                if (!show_tooltip || $target.attr('title') !== undefined) {
                    return;
                }
                $target.tooltip({title: _t('Double-click to edit'), trigger: 'manuel', container: 'body'}).tooltip('show');
                setTimeout(function () {
                    $target.tooltip('dispose');
                }, 800);
            }, 400);
        });
    }
};
var fn_detach = eventHandler.detach;
eventHandler.detach = function (oLayoutInfo, options) {
    fn_detach.call(this, oLayoutInfo, options);
    oLayoutInfo.editable().off('mousedown');
    oLayoutInfo.editor().off("dragstart");
    oLayoutInfo.editor().off('click');
    $(document).off('mousedown', summernote_mousedown);
    $(document).off('mouseup', summernote_mouseup);
    oLayoutInfo.editor().off("dblclick");
    $(document).off("keyup", reRangeSelectKey);
};

// Translation for odoo
$.summernote.lang.odoo = {
    font: {
      bold: _t('Bold'),
      italic: _t('Italic'),
      underline: _t('Underline'),
      strikethrough: _t('Strikethrough'),
      subscript: _t('Subscript'),
      superscript: _t('Superscript'),
      clear: _t('Remove Font Style'),
      height: _t('Line Height'),
      name: _t('Font Family'),
      size: _t('Font Size')
    },
    image: {
      image: _t('File / Image'),
      insert: _t('Insert Image'),
      resizeFull: _t('Resize Full'),
      resizeHalf: _t('Resize Half'),
      resizeQuarter: _t('Resize Quarter'),
      floatLeft: _t('Float Left'),
      floatRight: _t('Float Right'),
      floatNone: _t('Float None'),
      dragImageHere: _t('Drag an image here'),
      selectFromFiles: _t('Select from files'),
      url: _t('Image URL'),
      remove: _t('Remove Image')
    },
    link: {
      link: _t('Link'),
      insert: _t('Insert Link'),
      unlink: _t('Unlink'),
      edit: _t('Edit'),
      textToDisplay: _t('Text to display'),
      url: _t('To what URL should this link go?'),
      openInNewWindow: _t('Open in new window')
    },
    video: {
      video: _t('Video'),
      videoLink: _t('Video Link'),
      insert: _t('Insert Video'),
      url: _t('Video URL?'),
      providers: _t('(YouTube, Vimeo, Vine, Instagram, DailyMotion or Youku)')
    },
    table: {
      table: _t('Table')
    },
    hr: {
      insert: _t('Insert Horizontal Rule')
    },
    style: {
      style: _t('Style'),
      normal: _t('Normal'),
      blockquote: _t('Quote'),
      pre: _t('Code'),
      small: _t('Small'),
      h1: _t('Header 1'),
      h2: _t('Header 2'),
      h3: _t('Header 3'),
      h4: _t('Header 4'),
      h5: _t('Header 5'),
      h6: _t('Header 6')
    },
    lists: {
      unordered: _t('Unordered list'),
      ordered: _t('Ordered list')
    },
    options: {
      help: _t('Help'),
      fullscreen: _t('Full Screen'),
      codeview: _t('Code View')
    },
    paragraph: {
      paragraph: _t('Paragraph'),
      outdent: _t('Outdent'),
      indent: _t('Indent'),
      left: _t('Align left'),
      center: _t('Align center'),
      right: _t('Align right'),
      justify: _t('Justify full')
    },
    color: {
      custom: _t('Custom Color'),
      background: _t('Background Color'),
      foreground: _t('Font Color'),
      transparent: _t('Transparent'),
      setTransparent: _t('None'),
    },
    shortcut: {
      shortcuts: _t('Keyboard shortcuts'),
      close: _t('Close'),
      textFormatting: _t('Text formatting'),
      action: _t('Action'),
      paragraphFormatting: _t('Paragraph formatting'),
      documentStyle: _t('Document Style')
    },
    history: {
      undo: _t('Undo'),
      redo: _t('Redo')
    }
};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * @todo get rid of this. This has been implemented as a fix to be able to
 * instantiate media, link and alt dialogs outside the main editor: in the
 * simple HTML fields and forum textarea.
 */
var SummernoteManager = Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @constructor
     */
    init: function (parent) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        topBus.on('alt_dialog_demand', this, this._onAltDialogDemand);
        topBus.on('crop_image_demand', this, this._onCropImageDemand);
        topBus.on('link_dialog_demand', this, this._onLinkDialogDemand);
        topBus.on('media_dialog_demand', this, this._onMediaDialogDemand);
    },
    /**
     * @override
     */
    destroy: function () {
        mixins.EventDispatcherMixin.destroy.call(this);

        topBus.off('alt_dialog_demand', this, this._onAltDialogDemand);
        topBus.off('crop_image_demand', this, this._onCropImageDemand);
        topBus.off('link_dialog_demand', this, this._onLinkDialogDemand);
        topBus.off('media_dialog_demand', this, this._onMediaDialogDemand);
    },

    /**
     * Create modified image attachments.
     *
     * @param {jQuery} $editable
     * @returns {Promise}
     */
    saveModifiedImages: function ($editable) {
        const defs = _.map($editable, async editableEl => {
            const {oeModel: resModel, oeId: resId} = editableEl.dataset;
            const proms = [...editableEl.querySelectorAll('.o_modified_image_to_save')].map(async el => {
                const isBackground = !el.matches('img');
                el.classList.remove('o_modified_image_to_save');
                // Modifying an image always creates a copy of the original, even if
                // it was modified previously, as the other modified image may be used
                // elsewhere if the snippet was duplicated or was saved as a custom one.
                const newAttachmentSrc = await this._rpc({
                    route: `/web_editor/modify_image/${el.dataset.originalId}`,
                    params: {
                        res_model: resModel,
                        res_id: parseInt(resId),
                        data: (isBackground ? el.dataset.bgSrc : el.getAttribute('src')).split(',')[1],
                    },
                });
                if (isBackground) {
                    $(el).css('background-image', `url('${newAttachmentSrc}')`);
                    delete el.dataset.bgSrc;
                } else {
                    el.setAttribute('src', newAttachmentSrc);
                }
            });
            return Promise.all(proms);
        });
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a demand to open a alt dialog is received on the bus.
     *
     * @private
     * @param {Object} data
     */
    _onAltDialogDemand: function (data) {
        if (data.__alreadyDone) {
            return;
        }
        data.__alreadyDone = true;
        var altDialog = new weWidgets.AltDialog(this,
            data.options || {},
            data.media
        );
        if (data.onSave) {
            altDialog.on('save', this, data.onSave);
        }
        if (data.onCancel) {
            altDialog.on('cancel', this, data.onCancel);
        }
        altDialog.open();
    },
    /**
     * Called when a demand to crop an image is received on the bus.
     *
     * @private
     * @param {Object} data
     */
    _onCropImageDemand: function (data) {
        if (data.__alreadyDone) {
            return;
        }
        data.__alreadyDone = true;
        new weWidgets.ImageCropWidget(this, data.media)
            .appendTo(data.$editable);
    },
    /**
     * Called when a demand to open a link dialog is received on the bus.
     *
     * @private
     * @param {Object} data
     */
    _onLinkDialogDemand: function (data) {
        if (data.__alreadyDone) {
            return;
        }
        data.__alreadyDone = true;
        var linkDialog = new weWidgets.LinkDialog(this,
            data.options || {},
            data.$editable,
            data.linkInfo
        );
        if (data.onSave) {
            linkDialog.on('save', this, data.onSave);
        }
        if (data.onCancel) {
            linkDialog.on('cancel', this, data.onCancel);
        }
        linkDialog.open();
    },
    /**
     * Called when a demand to open a media dialog is received on the bus.
     *
     * @private
     * @param {Object} data
     */
    _onMediaDialogDemand: function (data) {
        if (data.__alreadyDone) {
            return;
        }
        data.__alreadyDone = true;

        var mediaDialog = new weWidgets.MediaDialog(this,
            _.extend({
                res_model: data.$editable.data('oe-model'),
                res_id: data.$editable.data('oe-id'),
                domain: data.$editable.data('oe-media-domain'),
            }, data.options),
            data.media
        );
        if (data.onSave) {
            mediaDialog.on('save', this, data.onSave);
        }
        if (data.onCancel) {
            mediaDialog.on('cancel', this, data.onCancel);
        }
        mediaDialog.open();
    },
});
return SummernoteManager;
});
