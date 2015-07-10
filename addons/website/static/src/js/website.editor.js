(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

openerp.define.active();

define(['summernote/summernote'], function () {

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* Summernote Lib (neek change to make accessible: method and object) */
    var agent = $.summernote.core.agent;
    var dom = $.summernote.core.dom;
    var range = $.summernote.core.range;
    var list = $.summernote.core.list;
    var key = $.summernote.core.key;
    var eventHandler = $.summernote.eventHandler;
    var renderer = $.summernote.renderer;
    var options = $.summernote.options;

    var tplButton = renderer.getTemplate().button;
    var tplIconButton = renderer.getTemplate().iconButton;

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* update and change the popovers content, and add history button */

    var fn_createPalette = renderer.createPalette;
    renderer.createPalette = function ($container, options) {
        fn_createPalette.call(this, $container, options);

        if (!openerp.qweb.has_template('website.colorpicker')) {
            return;
        }

        var $color = $container.find('.note-color');
        var html = openerp.qweb.render('website.colorpicker');
        $color.find('.note-color-palette').prepend(html);
        var $bg = $color.find('.colorpicker:first button');
        var $fore = $color.find('.colorpicker:last button');

        $bg.each(function () { $(this).attr('data-event', 'backColor').attr('data-value', $(this).attr('class')); });
        $fore.each(function () { $(this).attr('data-event', 'foreColor').attr('data-value', $(this).attr('class').replace(/bg-/, 'text-')); });
    };
    
    var fn_tplPopovers = renderer.tplPopovers;
    renderer.tplPopovers = function (lang, options) {
        var $popover = $(fn_tplPopovers.call(this, lang, options));

        var $imagePopover = $popover.find('.note-image-popover');
        var $linkPopover = $popover.find('.note-link-popover');
        var $airPopover = $popover.find('.note-air-popover');

        if (window === window.top) {
            $popover.children().addClass("hidden-xs");
        }

        //////////////// image popover

        // add center button for images
        var $centerbutton = $(tplIconButton('fa fa-align-center', {
                title: _t('Center'),
                event: 'floatMe',
                value: 'center'
            })).insertAfter($imagePopover.find('[data-event="floatMe"][data-value="left"]'));
        $imagePopover.find('button[data-event="removeMedia"]').parent().remove();
        $imagePopover.find('button[data-event="floatMe"][data-value="none"]').remove();

        var $alt = $('<div class="btn-group"/>');
        $alt.prependTo($imagePopover.find('.popover-content'));
        $alt.append('<button class="btn btn-default btn-sm btn-small" data-event="alt"><strong>Alt: </strong><span class="o_image_alt"></span></button>');

        // padding button
        var $padding = $('<div class="btn-group"/>');
        $padding.insertBefore($imagePopover.find('.btn-group:first'));
        var $button = $(tplIconButton('fa fa-plus-square-o', {
                title: _t('Padding'),
                dropdown: true
            })).appendTo($padding);
        var $ul = $('<ul class="dropdown-menu"/>').insertAfter($button);
        $ul.append('<li><a data-event="padding" href="#" data-value="">'+_t('None')+'</a></li>');
        $ul.append('<li><a data-event="padding" href="#" data-value="small">'+_t('Small')+'</a></li>');
        $ul.append('<li><a data-event="padding" href="#" data-value="medium">'+_t('Medium')+'</a></li>');
        $ul.append('<li><a data-event="padding" href="#" data-value="large">'+_t('Large')+'</a></li>');
        $ul.append('<li><a data-event="padding" href="#" data-value="xl">'+_t('Xl')+'</a></li>');

        // circle, boxed... options became toggled
        $imagePopover.find('[data-event="imageShape"]:not([data-value])').remove();
        var $button = $(tplIconButton('fa fa-sun-o', {
                title: _t('Shadow'),
                event: 'imageShape',
                value: 'shadow'
            })).insertAfter($imagePopover.find('[data-event="imageShape"][data-value="img-circle"]'));

        // add spin for fa
        var $spin = $('<div class="btn-group hidden only_fa"/>').insertAfter($button.parent());
        $(tplIconButton('fa fa-refresh', {
                title: _t('Spin'),
                event: 'imageShape',
                value: 'fa-spin'
            })).appendTo($spin);

        // resize for fa
        var $resizefa = $('<div class="btn-group hidden only_fa"/>')
            .insertAfter($imagePopover.find('.btn-group:has([data-event="resize"])'));
        for (var size=1; size<=5; size++) {
            $(tplButton('<span class="note-fontsize-10">'+size+'x</span>', {
              title: size+"x",
              event: 'resizefa',
              value: size+''
            })).appendTo($resizefa);
        }
        var $colorfa = $airPopover.find('.note-color').clone();
        $colorfa.find(".btn-group:first").remove();
        $colorfa.find("ul.dropdown-menu").css('min-width', '172px');
        $colorfa.find('button[data-event="color"]').attr('data-value', '{"foreColor": "#f00"}')
            .find("i").css({'background': '', 'color': '#f00'});
        $resizefa.after($colorfa);

        // show dialog box and delete
        var $imageprop = $('<div class="btn-group"/>');
        $imageprop.appendTo($imagePopover.find('.popover-content'));
        $(tplIconButton('fa fa-picture-o', {
                title: _t('Edit'),
                event: 'showImageDialog'
            })).appendTo($imageprop);
        $(tplIconButton('fa fa-trash-o', {
                title: _t('Remove'),
                event: 'delete'
            })).appendTo($imageprop);

        $imagePopover.find('.popover-content').append($airPopover.find(".note-history").clone());

        $imagePopover.find('[data-event="showImageDialog"]').before($airPopover.find('[data-event="showLinkDialog"]').clone());
        
        //////////////// link popover

        $linkPopover.find('.popover-content').append($airPopover.find(".note-history").clone());

        $linkPopover.find('button[data-event="showLinkDialog"] i').attr("class", "fa fa-link");
        $linkPopover.find('button[data-event="unlink"]').before($airPopover.find('button[data-event="showImageDialog"]').clone());

        //////////////// text/air popover

        //// highlight the text format
        $airPopover.find('.note-style').on('mousedown', function () {
            var $format = $airPopover.find('[data-event="formatBlock"]');
            var node = range.create().sc;
            var formats = $format.map(function () { return $(this).data("value"); }).get();
            while (node && (!node.tagName || (!node.tagName || formats.indexOf(node.tagName.toLowerCase()) === -1))) {
                node = node.parentNode;
            }
            $format.parent().removeClass('active');
            $format.filter('[data-value="'+(node ? node.tagName.toLowerCase() : "p")+'"]')
                .parent().addClass("active");
        });

        //////////////// tooltip

        $airPopover.add($linkPopover).add($imagePopover).find("button")
            .tooltip('destroy')
            .tooltip({
                container: 'body',
                trigger: 'hover',
                placement: 'bottom'
            }).on('click', function () {$(this).tooltip('hide');});

        return $popover;
    };

    var fn_boutton_update = eventHandler.popover.button.update;
    eventHandler.popover.button.update = function ($container, oStyle) {
        // stop animation when edit content
        var previous = $(".note-control-selection").data('target');
        if (previous) {
            $(previous).css({"-webkit-animation-play-state": "", "animation-play-state": "", "-webkit-transition": "", "transition": "", "-webkit-animation": "", "animation": ""});
        }
        if (oStyle.image) {
            $(oStyle.image).css({"-webkit-animation": "none", "animation": "none"});
        }
        // end

        fn_boutton_update.call(this, $container, oStyle);

        $container.find('button[data-event="undo"]').attr('disabled', !history.hasUndo());
        $container.find('button[data-event="redo"]').attr('disabled', !history.hasRedo());

        if (oStyle.image) {
            $container.find('[data-event]').parent().removeClass("active");

            $container.find('a[data-event="padding"][data-value="small"]').parent().toggleClass("active", $(oStyle.image).hasClass("padding-small"));
            $container.find('a[data-event="padding"][data-value="medium"]').parent().toggleClass("active", $(oStyle.image).hasClass("padding-medium"));
            $container.find('a[data-event="padding"][data-value="large"]').parent().toggleClass("active", $(oStyle.image).hasClass("padding-large"));
            $container.find('a[data-event="padding"][data-value="xl"]').parent().toggleClass("active", $(oStyle.image).hasClass("padding-xl"));
            $container.find('a[data-event="padding"][data-value=""]').parent().toggleClass("active", !$container.find('.active a[data-event="padding"]').length);

            if (dom.isImgFont(oStyle.image)) {

                $container.find('.btn-group:not(.only_fa):has(button[data-event="resize"],button[data-event="imageShape"])').addClass("hidden");
                $container.find('.only_fa').removeClass("hidden");
                $container.find('button[data-event="resizefa"][data-value="2"]').toggleClass("active", $(oStyle.image).hasClass("fa-2x"));
                $container.find('button[data-event="resizefa"][data-value="3"]').toggleClass("active", $(oStyle.image).hasClass("fa-3x"));
                $container.find('button[data-event="resizefa"][data-value="4"]').toggleClass("active", $(oStyle.image).hasClass("fa-4x"));
                $container.find('button[data-event="resizefa"][data-value="5"]').toggleClass("active", $(oStyle.image).hasClass("fa-5x"));
                $container.find('button[data-event="resizefa"][data-value="1"]').toggleClass("active", !$container.find('.active[data-event="resizefa"]').length);

                $container.find('button[data-event="imageShape"][data-value="fa-spin"]').toggleClass("active", $(oStyle.image).hasClass("fa-spin"));
                
                $container.find('.note-color').removeClass("hidden");

            } else {

                $container.find('.hidden:not(.only_fa)').removeClass("hidden");
                $container.find('.only_fa').addClass("hidden");
                var width = ($(oStyle.image).attr('style') || '').match(/(^|;|\s)width:\s*([0-9]+%)/);
                if (width) {
                    width = width[2];
                }
                $container.find('button[data-event="resize"][data-value="1"]').toggleClass("active", width === "100%");
                $container.find('button[data-event="resize"][data-value="0.5"]').toggleClass("active", width === "50%");
                $container.find('button[data-event="resize"][data-value="0.25"]').toggleClass("active", width === "25%");

                $container.find('button[data-event="imageShape"][data-value="shadow"]').toggleClass("active", $(oStyle.image).hasClass("shadow"));
                
                if (!$(oStyle.image).is("img")) {
                    $container.find('.btn-group:has(button[data-event="imageShape"])').addClass("hidden");
                }

                $container.find('.note-color').addClass("hidden");

            }

            $container.find('button[data-event="floatMe"][data-value="left"]').toggleClass("active", $(oStyle.image).hasClass("pull-left"));
            $container.find('button[data-event="floatMe"][data-value="center"]').toggleClass("active", $(oStyle.image).hasClass("center-block"));
            $container.find('button[data-event="floatMe"][data-value="right"]').toggleClass("active", $(oStyle.image).hasClass("pull-right"));

            $(oStyle.image).trigger('attributes_change');
        }
    };

    var fn_popover_update = eventHandler.popover.update;
    eventHandler.popover.update = function ($popover, oStyle, isAirMode) {
        var $imagePopover = $popover.find('.note-image-popover');
        var $linkPopover = $popover.find('.note-link-popover');
        var $airPopover = $popover.find('.note-air-popover');

        fn_popover_update.call(this, $popover, oStyle, isAirMode);

        if (!isAirMode || $(oStyle.range.sc).closest('[data-oe-model]:not([data-oe-model="ir.ui.view"]):not([data-oe-type="html"])').length) {
            $imagePopover.hide();
            $linkPopover.hide();
            $airPopover.hide();
            return;
        }

        if (oStyle.image) {
            if (oStyle.image.parentNode.className.match(/(^|\s)media_iframe_video(\s|$)/i)) {
                oStyle.image = oStyle.image.parentNode;
            }
            var alt =  $(oStyle.image).attr("alt");

            $imagePopover.find('.o_image_alt').text( (alt || "").replace(/&quot;/g, '"') ).parent().toggle(oStyle.image.tagName === "IMG");
            $imagePopover.show();

            range.createFromNode(dom.firstChild(oStyle.image)).select();
        } else {
            $(".note-control-selection").hide();
        }

        if (oStyle.image || (!oStyle.range.isCollapsed() || (oStyle.range.sc.tagName && !dom.isAnchor(oStyle.range.sc)) || (oStyle.image && !$(oStyle.image).closest('a').length))) {
            $linkPopover.hide();
            oStyle.anchor = false;
        }

        if (oStyle.image || oStyle.anchor || !$(oStyle.range.sc).closest('.note-editable').length) {
            $airPopover.hide();
        } else {
            $airPopover.show();
        }
    };

    eventHandler.handle.update = function ($handle, oStyle, isAirMode) {
        $handle.toggle(!!oStyle.image);
        if (oStyle.image) {
            var $selection = $handle.find('.note-control-selection');
            var $image = $(oStyle.image);
            var szImage = {
              w: parseInt($image.outerWidth(true), 10),
              h: parseInt($image.outerHeight(true), 10)
            };
            $selection.data('target', oStyle.image); // save current image element.
            var sSizing = szImage.w + 'x' + szImage.h;
            $selection.find('.note-control-selection-info').text(szImage.h > 50 ? sSizing : "");

            $selection.find('.note-control-sizing').toggleClass('note-control-sizing note-control-holder').css({
                    'border-top': 0,
                    'border-left': 0
                });
        }
    };

    $(document).on('click keyup', function () {
        $('button[data-event="undo"]').attr('disabled', !history.hasUndo());
        $('button[data-event="redo"]').attr('disabled', !history.hasRedo());
    });

    eventHandler.editor.undo = function ($popover) {
        if(!$popover.attr('disabled')) history.undo();
    };
    eventHandler.editor.redo = function ($popover) {
        if(!$popover.attr('disabled')) history.redo();
    };

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* hack for image and link editor */

    function getImgTarget () {
      return $(".note-control-selection").data('target');
    }
    eventHandler.editor.padding = function ($editable, sValue) {
        var $target = $(getImgTarget());
        var paddings = "small medium large xl".split(/\s+/);
        $editable.data('NoteHistory').recordUndo();
        if (sValue.length) {
            paddings.splice(paddings.indexOf(sValue),1);
            $target.toggleClass('padding-'+sValue);
        }
        $target.removeClass("padding-" + paddings.join(" padding-"));
    };
    eventHandler.editor.resize = function ($editable, sValue) {
        var $target = $(getImgTarget());
        $editable.data('NoteHistory').recordUndo();
        var width = ($target.attr('style') || '').match(/(^|;|\s)width:\s*([0-9]+)%/);
        if (width) {
            width = width[2]/100;
        }
        $(getImgTarget()).css('width', width != sValue ? (sValue * 100) + '%' : '');
    };
    eventHandler.editor.resizefa = function ($editable, sValue) {
        var $target = $(getImgTarget());
        $editable.data('NoteHistory').recordUndo();
        $target.attr('class', $target.attr('class').replace(/\s*fa-[0-9]+x/g, ''));
        if (+sValue > 1) {
            $target.addClass('fa-'+sValue+'x');
        }
    };
    eventHandler.editor.floatMe = function ($editable, sValue) {
        var $target = $(getImgTarget());
        $editable.data('NoteHistory').recordUndo();
        switch (sValue) {
            case 'center': $target.toggleClass('center-block').removeClass('pull-right pull-left'); break;
            case 'left': $target.toggleClass('pull-left').removeClass('pull-right center-block'); break;
            case 'right': $target.toggleClass('pull-right').removeClass('pull-left center-block'); break;
        }
    };
    eventHandler.editor.imageShape = function ($editable, sValue) {
        var $target = $(getImgTarget());
        $editable.data('NoteHistory').recordUndo();
        $target.toggleClass(sValue);
    };

    eventHandler.dialog.showLinkDialog = function ($editable, $dialog, linkInfo) {
        $editable.data('range').select();
        $editable.data('NoteHistory').recordUndo();
        
        var editor = new website.editor.LinkDialog($editable, linkInfo);
        editor.appendTo(document.body);

        var def = new $.Deferred();
        editor.on("save", this, function (linkInfo) {
            linkInfo.range.select();
            $editable.data('range', linkInfo.range);
            def.resolve(linkInfo);
            $('.note-popover .note-link-popover').show();
        });
        editor.on("cancel", this, function () {
            def.reject();
        });
        return def;
    };
    eventHandler.dialog.showImageDialog = function ($editable) {
        var r = $editable.data('range');
        if (r.sc.tagName && r.sc.childNodes.length) {
            r.sc = r.sc.childNodes[r.so];
        }
        var editor = new website.editor.MediaDialog($editable, dom.isImg(r.sc) ? r.sc : null);
        editor.appendTo(document.body);
        return new $.Deferred().reject();
    };
    $.summernote.pluginEvents.alt = function (event, editor, layoutInfo, sorted) {
        var $editable = layoutInfo.editable();
        var $selection = layoutInfo.handle().find('.note-control-selection');
        var media = $selection.data('target');
        new website.editor.alt($editable, media).appendTo(document.body);
    };

    //////////////////////////////////////////////////////////////////////////////////////////////////////////

    dom.isVoid = function (node) {
        return node && /^BR|^IMG|^HR/.test(node.nodeName.toUpperCase()) || dom.isImg(node);
    };
    dom.isImg = function (node) {
        return dom.isImgFont(node) || (node && (node.nodeName === "IMG" || (node.className && node.className.match(/(^|\s)media_iframe_video(\s|$)/i)) ));
    };
    dom.isForbiddenNode = function (node) {
        return $(node).is(".media_iframe_video, .fa, img");
    };

    dom.isImgFont = function (node) {
        var nodeName = node && node.nodeName.toUpperCase();
        var className = (node && node.className || "");
        if (node && (nodeName === "SPAN" || nodeName === "I") && className.length) {
            var classNames = className.split(/\s+/);
            for (var k=0; k<website.editor.fontIcons.length; k++) {
                if (_.intersection(website.editor.fontIcons[k].icons, classNames).length) {
                    return true;
                }
            }
        }
        return false;
    };
    // re-overwrite font to include theme icons
    var isFont = dom.isFont;
    dom.isFont = function (node) {
        return dom.isImgFont(node) || isFont(node);
    };

    //////////////////////////////////////////////////////////////////////////////////////////////////////////

    var fn_visible = $.summernote.pluginEvents.visible;
    $.summernote.pluginEvents.visible = function (event, editor, layoutInfo) {
        var res = fn_visible.call(this, event, editor, layoutInfo);
        var $node = $(dom.node(range.create().sc));
        if (($node.is('[data-oe-type="html"]') || $node.is('[data-oe-field="arch"]')) && $node.hasClass("o_editable") && !$node[0].children.length) {
            var p = $('<p><br/></p>')[0];
            $node.append( p );
            range.createFromNode(p.firstChild).select();
        }
        return res;
    };

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* fix ie and re-range to don't break snippet*/

    var initial_data = {};
    function reRangeSelectKey (event) {
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
    function reRangeSelect (event, dx, dy) {
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
    function summernote_mouseup (event) {
        if ($(event.target).closest("#website-top-navbar, .note-popover").length) {
            return;
        }
        // don't rerange if simple click
        if (initial_data.event) {
            var dx = event.clientX - (event.shiftKey ? initial_data.rect.left : initial_data.event.clientX);
            var dy = event.clientY - (event.shiftKey ? initial_data.rect.top : initial_data.event.clientY);
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
    function summernote_mousedown (event) {
        history.splitNext();

        var $editable = $(event.target).closest(".o_editable, .note-editor");
        
        if (!!document.documentMode) {
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

        // remember_selection when click on non editable area
        var r = range.create();
        if ($(r ? dom.node(r.sc) : event.srcElement || event.target).closest('#website-top-navbar, #oe_main_menu_navbar, .note-popover, .note-toolbar, .modal').length) {
            if (!$(event.target).is('input, select, label, button, a')) {
                if (!remember_selection && $editable[0]) {
                    remember_selection = range.create(dom.firstChild($editable[0]), 0);
                }
                try {
                    remember_selection.select();
                } catch (e) {
                    console.warn(e);
                }
            }
        } else if (r && $(dom.node(r.sc)).closest('.o_editable, .note-editable').length) {
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

    var last_div;
    var last_div_change;
    var last_editable;
    function summernote_ie_fix (event, pred) {
        var editable;
        var div;
        var node = event.target;
        while(node.parentNode) {
            if (!div && pred(node)) {
                div = node;
            }
            if(last_div !== node && (node.getAttribute('contentEditable')==='false' || node.className && (node.className.indexOf('o_not_editable') !== -1))) {
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
        oLayoutInfo.editor.on('dragstart', 'img', function (e) { e.preventDefault(); });
        $(document).on('mousedown', summernote_mousedown);
        $(document).on('mouseup', summernote_mouseup);
        oLayoutInfo.editor.off('click').on('click', function (e) {e.preventDefault();}); // if the content editable is a link
        oLayoutInfo.editor.on('dblclick', 'img, .media_iframe_video, span.fa, i.fa, span.fa', function (event) {
            if (!$(event.target).closest(".note-toolbar").length) { // prevent icon edition of top bar for default summernote
                new website.editor.MediaDialog(oLayoutInfo.editor, event.target).appendTo(document.body);
            }
        });
        $(document).on("keyup", reRangeSelectKey);
        
        var clone_data = false;
        var $node = oLayoutInfo.editor;
        if ($node.data('oe-model')) {
            $node.on('content_changed', function () {

            var $nodes = $('[data-oe-model]')
                .filter(function () { return this != $node[0];})
                .filter('[data-oe-model="'+$node.data('oe-model')+'"]')
                .filter('[data-oe-id="'+$node.data('oe-id')+'"]')
                .filter('[data-oe-field="'+$node.data('oe-field')+'"]');
            if ($node.data('oe-type')) $nodes = $nodes.filter('[data-oe-type="'+$node.data('oe-type')+'"]');
            if ($node.data('oe-expression')) $nodes = $nodes.filter('[data-oe-expression="'+$node.data('oe-expression')+'"]');
            if ($node.data('oe-xpath')) $nodes = $nodes.filter('[data-oe-xpath="'+$node.data('oe-xpath')+'"]');
            if ($node.data('oe-contact-options')) $nodes = $nodes.filter('[data-oe-contact-options="'+$node.data('oe-contact-options')+'"]');

            var nodes = $node.get();

            if ($node.data('oe-type') === "many2one") {
                $nodes = $nodes.add($('[data-oe-model]')
                    .filter(function () { return this != $node[0] && nodes.indexOf(this) === -1; })
                    .filter('[data-oe-many2one-model="'+$node.data('oe-many2one-model')+'"]')
                    .filter('[data-oe-many2one-id="'+$node.data('oe-many2one-id')+'"]')
                    .filter('[data-oe-type="many2one"]'));

                $nodes = $nodes.add($('[data-oe-model]')
                    .filter(function () { return this != $node[0] && nodes.indexOf(this) === -1; })
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
    };
    var fn_dettach = eventHandler.dettach;
    eventHandler.dettach = function (oLayoutInfo, options) {
        fn_dettach.call(this, oLayoutInfo, options);
        oLayoutInfo.editor.off("dragstart");
        $(document).off('mousedown', summernote_mousedown);
        $(document).off('mouseup', summernote_mouseup);
        oLayoutInfo.editor.off("dblclick");
        $(document).off("keyup", reRangeSelectKey);
    };

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* Translation for odoo */

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
          image: _t('Picture'),
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
          recent: _t('Recent Color'),
          more: _t('More Color'),
          background: _t('Background Color'),
          foreground: _t('Foreground Color'),
          transparent: _t('Transparent'),
          setTransparent: _t('Set transparent'),
          reset: _t('Reset'),
          resetToDefault: _t('Reset to default')
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

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    /* Change History to have a global History for all summernote instances */

    var History = function History ($editable) {
        var aUndo = [];
        var pos = 0;

        this.makeSnap = function () {
            var rng = range.create(),
                elEditable = dom.ancestor(rng && rng.commonAncestor(), dom.isEditable) || $('.o_editable:first')[0];
            return {
                editable: elEditable,
                contents: elEditable.innerHTML,
                bookmark: rng && rng.bookmark(elEditable),
                scrollTop: $(elEditable).scrollTop()
            };
        };

        this.applySnap = function (oSnap) {
            var $editable = $(oSnap.editable);

            if (!!document.documentMode) {
                $editable.removeAttr("contentEditable").removeProp("contentEditable");
            }

            $editable.html(oSnap.contents).scrollTop(oSnap.scrollTop);
            $(".oe_overlay").remove();
            $(".note-control-selection").hide();
            
            $editable.trigger("content_changed");

            if (!oSnap.bookmark) {
                return;
            }

            try {
                var r = range.createFromBookmark(oSnap.editable, oSnap.bookmark);
                r.select();
            } catch(e) {
                console.error(e);
                return;
            }

            $(document).trigger("click");
            $(".o_editable *").filter(function () {
                var $el = $(this);
                if($el.data('snippet-editor')) {
                    $el.removeData();
                }
            });

            setTimeout(function () {
                var target = dom.isBR(r.sc) ? r.sc.parentNode : dom.node(r.sc);
                if (!target) {
                    return;
                }
                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("mousedown", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
                target.dispatchEvent(evt);

                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
                target.dispatchEvent(evt);
            },0);
        };

        this.undo = function () {
            if (!pos) { return; }
            last = null;
            if (!aUndo[pos]) aUndo[pos] = this.makeSnap();
            if (aUndo[pos-1].jump) pos--;
            this.applySnap(aUndo[--pos]);
        };
        this.hasUndo = function () {
            return pos > 0;
        };

        this.redo = function () {
            if (aUndo.length <= pos+1) { return; }
            if (aUndo[pos].jump) pos++;
            this.applySnap(aUndo[++pos]);
        };
        this.hasRedo = function () {
            return aUndo.length > pos+1;
        };

        var last;
        this.recordUndo = function ($editable, event, internal_history) {
            if (!internal_history) {
                if (!event || !last || !aUndo[pos-1] || aUndo[pos-1].editable !== $editable[0]) { // don't trigger change for all keypress
                    $(".o_editable.note-editable").trigger("content_changed");
                }
            }
            if (event) {
                if (last && aUndo[pos-1] && aUndo[pos-1].editable !== $editable[0]) {
                    // => make a snap when the user change editable zone (because: don't make snap for each keydown)
                    aUndo.splice(pos, aUndo.length);
                    var prev = aUndo[pos-1];
                    aUndo[pos] = {
                        editable: prev.editable,
                        contents: $(prev.editable).html(),
                        bookmark: prev.bookmark,
                        scrollTop: prev.scrollTop,
                        jump: true
                    };
                    pos++;
                }
                else if (event === last) return;
            }
            last = event;
            aUndo.splice(pos, aUndo.length);
            aUndo[pos] = this.makeSnap($editable);
            pos++;
        };

        this.splitNext = function () {
            last = false;
        };
    };
    var history = new History();

    //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // add focusIn to jQuery to allow to move caret into a div of a contentEditable area

    $.fn.extend({
        focusIn: function () {
            if (this.length) {
                range.create(dom.firstChild(this[0]), 0).select();
            }
            return this;
        },
        selectContent: function () {
            if (this.length) {
                var next = dom.lastChild(this[0]);
                range.create(dom.firstChild(this[0]), 0, next, next.textContent.length).select();
            }
            return this;
        },
        activateBlock: function () {
            var target = website.snippet.globalSelector.closest($(this))[0] || (dom.isBR(this) ? this.parentNode : dom.node(this));
            var evt = document.createEvent("MouseEvents");
            evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
            target.dispatchEvent(evt);
            return this;
        }
    });

    //////////////////////////////////////////////////////////////////////////////////////////////////////////

    function change_default_bootstrap_animation_to_edit() {
        var fn_carousel = $.fn.carousel;
        $.fn.carousel = function () {
            var res = fn_carousel.apply(this, arguments);
            // off bootstrap keydown event to remove event.preventDefault()
            // and allow to change cursor position
            $(this).off('keydown.bs.carousel');
            return res;
        };
    }

    //////////////////////////////////////////////////////////////////////////////////////////////////////////

    website.no_editor = !!$(document.documentElement).data('editable-no-editor');

    website.add_template_file('/website/static/src/xml/website.editor.xml');
    website.dom_ready.done(function () {
        website.ready().then(website.init_editor);

        $(document).on('click', 'a.js_link2post', function (ev) {
            ev.preventDefault();
            website.form(this.pathname, 'POST');
        });

        $(document).on('click', '.note-editable', function (ev) {
            ev.preventDefault();
        });

        $(document).on('submit', '.note-editable form .btn', function (ev) {
            // Disable form submition in editable mode
            ev.preventDefault();
        });

        $(document).on('hide.bs.dropdown', '.dropdown', function (ev) {
            // Prevent dropdown closing when a contenteditable children is focused
            if (ev.originalEvent
                    && $(ev.target).has(ev.originalEvent.target).length
                    && $(ev.originalEvent.target).is('[contenteditable]')) {
                ev.preventDefault();
            }
        });
    });

    website.init_editor = function () {
        var editor = new website.EditorBar();
        var $body = $(document.body);
        editor.prependTo($body).then(function () {
            if (location.search.indexOf("enable_editor") >= 0) {
                editor.edit();
            }
        });
        website.editor_bar = editor;
    };
    
    /* ----- TOP EDITOR BAR FOR ADMIN ---- */
    website.EditorBar = openerp.Widget.extend({
        template: 'website.editorbar',
        events: {
            'click button[data-action=save]': 'save',
            'click a[data-action=cancel]': 'cancel',
        },
        start: function() {
            var self = this;
            this.saving_mutex = new openerp.Mutex();

            this.$buttons = {
                edit: this.$el.parents().find('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
            };

            this.$('#website-top-edit').hide();
            this.$('#website-top-view').show();

            var $edit_button = this.$buttons.edit
                    .prop('disabled', website.no_editor);
            if (website.no_editor) {
                var help_text = $(document.documentElement).data('editable-no-editor');
                $edit_button.parent()
                    // help must be set on form above button because it does
                    // not appear on disabled button
                    .attr('title', help_text);
            }

            $('.dropdown-toggle').dropdown();

            this.$buttons.edit.click(function(ev) {
                self.edit();
            });

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));
            this.rte.on('rte:ready', this, function () {
                self.trigger('rte:ready');
            });

            this.rte.appendTo(this.$('#website-top-edit .nav.js_editor_placeholder'));
            return this._super.apply(this, arguments);
        },
        edit: function (no_editor) {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$el.show();
            this.$('#website-top-edit').show();
            
            if (!no_editor) {
                this.rte.start_edition();
                this.trigger('rte:called');
            }

            var flag = false;
            window.onbeforeunload = function(event) {
                if ($('.o_editable.o_dirty').length && !flag) {
                    flag = true;
                    setTimeout(function () {flag=false;},0);
                    return _t('This document is not saved!');
                }
            };
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        _save: function () {
            var self = this;

            var saved = {}; // list of allready saved views and data

            var defs = $('.o_editable')
                .filter('.o_dirty')
                .removeAttr('contentEditable')
                .removeClass('o_dirty o_editable oe_carlos_danger o_is_inline_editable')
                .map(function () {
                    var $el = $(this);

                    // remove multi edition
                    var key =  $el.data('oe-model')+":"+$el.data('oe-id')+":"+$el.data('oe-field')+":"+$el.data('oe-type')+":"+$el.data('oe-expression');
                    if (saved[key]) return true;
                    saved[key] = true;

                    // TODO: Add a queue with concurrency limit in webclient
                    // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                    return self.saving_mutex.exec(function () {
                        return self.saveElement($el)
                            .then(undefined, function (thing, response) {
                                // because ckeditor regenerates all the dom,
                                // we can't just setup the popover here as
                                // everything will be destroyed by the DOM
                                // regeneration. Add markings instead, and
                                // returns a new rejection with all relevant
                                // info
                                var id = _.uniqueId('carlos_danger_');
                                $el.addClass('o_dirty oe_carlos_danger');
                                $el.addClass(id);
                                return $.Deferred().reject({
                                    id: id,
                                    error: response.data,
                                });
                            });
                    });
                }).get();
            return $.when.apply(null, defs).then(function () {
                window.onbeforeunload = null;
                website.reload();
            }, function (failed) {
                // If there were errors, re-enable edition
                self.rte.start_edition(true);
                // jquery's deferred being a pain in the ass
                if (!_.isArray(failed)) { failed = [failed]; }

                _(failed).each(function (failure) {
                    var html = failure.error.exception_type === "except_osv";
                    if (html) {
                        var msg = $("<div/>").text(failure.error.message).html();
                        var data = msg.substring(3,msg.length-2).split(/', u'/);
                        failure.error.message = '<b>' + data[0] + '</b>' + dom.blank + data[1];
                    }
                    $(root).find('.' + failure.id)
                        .removeClass(failure.id)
                        .popover({
                            html: html,
                            trigger: 'hover',
                            content: failure.error.message,
                            placement: 'auto top',
                        })
                        // Force-show popovers so users will notice them.
                        .popover('show');
                });
            });
        },
        save: function () {
            return this._save().then(function () {
                website.reload();
            });
        },
        /**
         * Saves an RTE content, which always corresponds to a view section (?).
         */
        save_without_reload: function () {
            return this._save();
        },
        saveElement: function ($el) {
            var markup = $el.prop('outerHTML');
            return openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'save',
                args: [$el.data('oe-id'), markup,
                       $el.data('oe-xpath') || null,
                       website.get_context()],
            });
        },
        cancel: function () {
            new $.Deferred(function (d) {
                var $dialog = $(openerp.qweb.render('website.editor.discard')).appendTo(document.body);
                $dialog.on('click', '.btn-danger', function () {
                    d.resolve();
                }).on('hidden.bs.modal', function () {
                    d.reject();
                });
                d.always(function () {
                    $dialog.remove();
                });
                $dialog.modal('show');
            }).then(function () {
                window.onbeforeunload = null;
                website.reload();
            });
        },
    });
    
    website.EditorBarCustomize = openerp.Widget.extend({
        events: {
            'mousedown a.dropdown-toggle': 'load_menu',
            'click ul a[data-view-id]': 'do_customize',
        },
        start: function() {
            var self = this;
            this.$menu = self.$el.find('ul');
            this.view_name = $(document.documentElement).data('view-xmlid');
            if (!this.view_name) {
                this.$el.hide();
            }
            this.loaded = false;
        },
        load_menu: function () {
            var self = this;
            if(this.loaded) {
                return;
            }
            openerp.jsonRpc('/website/customize_template_get', 'call', { 'key': this.view_name }).then(
                function(result) {
                    _.each(result, function (item) {
                        if (item.key === "website.debugger" && !window.location.search.match(/[&?]debug(&|$)/)) return;
                        if (item.header) {
                            self.$menu.append('<li class="dropdown-header">' + item.name + '</li>');
                        } else {
                            self.$menu.append(_.str.sprintf('<li role="presentation"><a href="#" data-view-id="%s" role="menuitem"><strong class="fa fa%s-square-o"></strong> %s</a></li>',
                                item.id, item.active ? '-check' : '', item.name));
                        }
                    });
                    self.loaded = true;
                }
            );
        },
        do_customize: function (event) {
            var view_id = $(event.currentTarget).data('view-id');
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.ui.view',
                method: 'toggle',
                args: [],
                kwargs: {
                    ids: [parseInt(view_id, 10)],
                    context: website.get_context()
                }
            }).then( function() {
                window.location.reload();
            });
        },
    });

    $(document).ready(function() {
        var editorBarCustomize = new website.EditorBarCustomize();
        editorBarCustomize.setElement($('li[id=customize-menu]'));
        editorBarCustomize.start();
    });

    /* ----- RICH TEXT EDITOR ---- */

    website.RTE = openerp.Widget.extend({
        init: function (EditorBar) {
            this.EditorBar = EditorBar;
            $('.inline-media-link').remove();
            this._super.apply(this, arguments);

            computeFonts();
        },
        /**
         * Add a record undo to history
         * @param {DOM} target where the dom is changed is editable zone
         */
        historyRecordUndo: function ($target, internal_history) {
            var rng = range.create();
            var $editable = $($target || (rng && rng.sc)).closest(".o_editable");
            if ($editable.length) {
                rng = $editable.data('range') || rng;
            }
            if (!rng && $target.length) {
                rng = range.create($target.closest("*")[0],0);
            }
            if (rng) {
                try {
                    rng.select();
                } catch (e) {
                    console.error(e);
                }
            }
            $target = $(rng.sc);
            $target.mousedown();
            this.history.recordUndo($target, null, internal_history);
            $target.mousedown();
        },
        /**
         * Makes the page editable
         *
         * @param {Boolean} [restart=false] in case the edition was already set
         *                                  up once and is being re-enabled.
         * @returns {$.Deferred} deferred indicating when the RTE is ready
         */
        start_edition: function (restart) {
            var self = this;

            change_default_bootstrap_animation_to_edit();

            this.history = history;

            // handler for cancel editor
            $(document).on('keydown', function (event) {
                if (event.keyCode === 27 && !$('.modal-content:visible').length) {
                    setTimeout(function () {
                        $('#website-top-navbar [data-action="cancel"]').click();
                        var $modal = $('.modal-content > .modal-body').parents(".modal:first");
                        $modal.off('keyup.dismiss.bs.modal');
                        setTimeout(function () {
                            $modal.on('keyup.dismiss.bs.modal', function () {
                                $(this).modal('hide');
                            });
                        },500);
                    },0);
                }
            });

            // activate editor
            var $last;
            $(document).on('mousedown', function (event) {
                var $target = $(event.target);
                var $editable = $target.closest('.o_editable');

                if (!$editable.size()) {
                    return;
                }

                if ($last && (!$editable.size() || $last[0] != $editable[0])) {
                    var $destroy = $last;
                    setTimeout(function () {$destroy.destroy();},150); // setTimeout to remove flickering when change to editable zone (re-create an editor)
                    $last = null;
                }
                if ($editable.size() && (!$last || $last[0] != $editable[0]) &&
                        ($target.closest('[contenteditable]').attr('contenteditable') || "").toLowerCase() !== 'false') {
                    $editable.summernote(self._config());
                    $editable.data('NoteHistory', self.history);
                    $editable.data('rte', self);
                    $last = $editable;

                    // firefox & IE fix
                    try {
                        document.execCommand('enableObjectResizing', false, false);
                        document.execCommand('enableInlineTableEditing', false, false);
                        document.execCommand( '2D-position', false, false);
                    } catch (e) {}
                    document.body.addEventListener('resizestart', function (evt) {evt.preventDefault(); return false;});
                    document.body.addEventListener('movestart', function (evt) {evt.preventDefault(); return false;});
                    document.body.addEventListener('dragstart', function (evt) {evt.preventDefault(); return false;});

                    if (!range.create()) {
                        range.create($editable[0],0).select();
                    }

                    $target.trigger('mousedown'); // for activate selection on picture
                    setTimeout(function () {
                        self.historyRecordUndo($editable, true);
                    },0);
                }
            });

            $('.o_not_editable').attr("contentEditable", false);

            $('#wrapwrap [data-oe-model]')
                .not('.o_not_editable')
                .filter(function () {
                    return !$(this).closest('.o_not_editable').length;
                })
                .not('link, script')
                .not('[data-oe-readonly]')
                .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
                .not('.oe_snippet_editor')
                .addClass('o_editable');

            $('.o_editable').each(function () {
                var node = this;
                var $node = $(node);

                // add class to display inline-block for empty t-field
                if(window.getComputedStyle(node).display === "inline" && $node.data('oe-type') !== "image") {
                    $node.addClass('o_is_inline_editable');
                }

                // start element observation
                $(node).one('content_changed', function () {
                    $node.addClass('o_dirty');
                });
                $(node).on('content_changed', function () {
                    self.trigger('change');
                });
            });

            $(document).trigger('mousedown');

            if (!restart) {
                $('#wrapwrap, .o_editable').on('click', '*', function (event) {
                    event.preventDefault();
                });

                $('body').addClass("editor_enable");

                $(document)
                    .tooltip({
                        selector: '[data-oe-readonly]',
                        container: 'body',
                        trigger: 'hover',
                        delay: { "show": 1000, "hide": 100 },
                        placement: 'bottom',
                        title: _t("Readonly field")
                    })
                    .on('click', function () {
                        $(this).tooltip('hide');
                    });

                self.trigger('rte:ready');
            }
        },

        _config: function () {
            return {
                airMode : true,
                focus: false,
                airPopover: [
                    ['style', ['style']],
                    ['font', ['bold', 'italic', 'underline', 'clear']],
                    ['fontsize', ['fontsize']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture']],
                    ['history', ['undo', 'redo']],
                ],
                oninit: function() {
                },
                styleWithSpan: false,
                inlinemedia : ['p'],
                lang: "odoo"
            };
        }
    });

    /* ----- EDITOR: LINK & MEDIA ---- */

    website.editor = { };
    website.editor.Dialog = openerp.Widget.extend({
        events: {
            'hidden.bs.modal': 'destroy',
            'click button.save': 'save',
            'click button[data-dismiss="modal"]': 'cancel',
        },
        init: function () {
            this._super();
        },
        start: function () {
            var sup = this._super();
            this.$el.modal({backdrop: 'static'});
            this.$('input:first').focus();
            return sup;
        },
        save: function () {
            this.close();
            this.trigger("saved");
        },
        cancel: function () {
            this.trigger("cancel");
        },
        close: function () {
            this.$el.modal('hide');
        },
        destroy: function () {
            this.$el.modal('hide').remove();
            if($(".modal.in").length>0){
                $('body').addClass('modal-open');
            }
        },
    });

    website.editor.LinkDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.link',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change :input.url-source': 'changed',
            'keyup :input.url': 'onkeyup',
            'keyup :input': 'preview',
            'click button.remove': 'remove_link',
            'change input#link-text': function (e) {
                this.text = $(e.target).val();
            },
            'change .link-style': function (e) {
                this.preview();
            },
        }),
        init: function (editable, linkInfo) {
            this._super(editable, linkInfo);
            this.editable = editable;
            this.data = linkInfo || {};

            this.data.className = "";
            if (this.data.range) {
                this.data.iniClassName = $(this.data.range.sc).filter("a").attr("class") || "";
                this.data.className = this.data.iniClassName.replace(/(^|\s+)btn(-[a-z0-9_-]*)?/gi, ' ');

                var is_link = this.data.range.isOnAnchor();
                var r = this.data.range;

                var sc = r.sc;
                var so = r.so;
                var ec = r.ec;
                var eo = r.eo;

                var nodes;
                if (!is_link) {
                    if (sc.tagName) {
                        sc = dom.firstChild(so ? sc.childNodes[so] : sc);
                        so = 0;
                    } else if (so !== sc.textContent.length) {
                        if (sc === ec) {
                            ec = sc = sc.splitText(so);
                            eo -= so;
                        } else {
                            sc = sc.splitText(so);
                        }
                        so = 0;
                    }
                    if (ec.tagName) {
                        ec = dom.lastChild(eo ? ec.childNodes[eo-1] : ec);
                        eo = ec.textContent.length;
                    } else if (eo !== ec.textContent.length) {
                        ec.splitText(eo);
                    }
                    
                    nodes = dom.listBetween(sc, ec);

                    // browsers can't target a picture or void node
                    if (dom.isVoid(sc) || dom.isImg(sc)) {
                      so = dom.listPrev(sc).length-1;
                      sc = sc.parentNode;
                    }
                    if (dom.isBR(ec)) {
                      eo = dom.listPrev(ec).length-1;
                      ec = ec.parentNode;
                    } else if (dom.isVoid(ec) || dom.isImg(sc)) {
                      eo = dom.listPrev(ec).length;
                      ec = ec.parentNode;
                    }

                    this.data.range = range.create(sc, so, ec, eo);
                    this.data.range.select();
                } else {
                    nodes = dom.ancestor(sc, dom.isAnchor).childNodes;
                }

                if (dom.isImg(sc) && nodes.indexOf(sc) === -1) {
                    nodes.push(sc);
                }
                if (nodes.length > 1 || dom.ancestor(nodes[0], dom.isImg)) {
                    var text = "";
                    this.data.images = [];
                    for (var i=0; i<nodes.length; i++) {
                        if (dom.ancestor(nodes[i], dom.isImg)) {
                            this.data.images.push(dom.ancestor(nodes[i], dom.isImg));
                            text += '[IMG]';
                        } else if (!is_link && i===0) {
                            text += nodes[i].textContent.slice(so, Infinity);
                        } else if (!is_link && i===nodes.length-1) {
                            text += nodes[i].textContent.slice(0, eo);
                        } else {
                            text += nodes[i].textContent;
                        }
                    }
                    this.data.text = text;
                }
            }

            this.data.text = this.data.text.replace(/[ \t\r\n]+/g, ' ');

            // Store last-performed request to be able to cancel/abort it.
            this.page_exists_req = null;
            this.search_pages_req = null;
            this.bind_data();
        },
        start: function () {
            var self = this;
            var last;
            this.$('#link-page').select2({
                minimumInputLength: 1,
                placeholder: _t("New or existing page"),
                query: function (q) {
                    if (q.term == last) return;
                    last = q.term;
                    $.when(
                        self.page_exists(q.term),
                        self.fetch_pages(q.term)
                    ).then(function (exists, results) {
                        var rs = _.map(results, function (r) {
                            return { id: r.loc, text: r.loc, };
                        });
                        if (!exists) {
                            rs.push({
                                create: true,
                                id: q.term,
                                text: _.str.sprintf(_t("Create page '%s'"), q.term),
                            });
                        }
                        q.callback({
                            more: false,
                            results: rs
                        });
                    }, function () {
                        q.callback({more: false, results: []});
                    });
                },
            });
            return this._super().then(this.proxy('bind_data'));
        },
        get_data: function (test) {
            var self = this,
                def = new $.Deferred(),
                $e = this.$('.active input.url-source').filter(':input'),
                val = $e.val(),
                label = this.$('#link-text').val() || val;

            if (label && this.data.images) {
                for(var i=0; i<this.data.images.length; i++) {
                    label = label.replace(/</, "&lt;").replace(/>/, "&gt;").replace(/\[IMG\]/, this.data.images[i].outerHTML);
                }
            }

            if (!test && (!val || !$e[0].checkValidity())) {
                // FIXME: error message
                $e.closest('.form-group').addClass('has-error');
                $e.focus();
                def.reject();
            }

            var style = this.$("input[name='link-style-type']:checked").val() || '';
            var size = this.$("input[name='link-style-size']:checked").val() || '';
            var classes = (this.data.className || "") + (style && style.length ? " btn " : "") + style + " " + size;
            var isNewWindow = this.$('input.window-new').prop('checked');

            var done = $.when();
            if ($e.hasClass('email-address') && $e.val().indexOf("@") !== -1) {
                def.resolve(val.indexOf("mailto:") === 0 ? val : 'mailto:' + val, isNewWindow, label, classes);
            } else if ($e.val() && $e.val().length && $e.hasClass('page')) {
                var data = $e.select2('data');
                if (test || !data.create) {
                    def.resolve(data.id, isNewWindow, label || data.text, classes);
                } else {
                    // Create the page, get the URL back
                    $.get(_.str.sprintf(
                            '/website/add/%s?noredirect=1', encodeURI(data.id)))
                        .then(function (response) {
                            def.resolve(response, isNewWindow, label, classes);
                        });
                }
            } else {
                def.resolve(val, isNewWindow, label, classes);
            }
            return def;
        },
        save: function () {
            var self = this;
            var _super = this._super.bind(this);
            return this.get_data()
                .then(function (url, new_window, label, classes) {
                    self.data.url = url;
                    self.data.newWindow = new_window;
                    self.data.text = label;
                    self.data.className = classes.replace(/\s+/gi, ' ').replace(/^\s+|\s+$/gi, '');

                    self.trigger("save", self.data);
                }).then(_super);
        },
        bind_data: function () {
            var href = this.data.url;
            var new_window = this.data.isNewWindow;
            var text = this.data.text;
            var classes = this.data.iniClassName;

            this.$('input#link-text').val(text);
            this.$('input.window-new').prop('checked', new_window);

            if (classes) {
                this.$('input[value!=""]').each(function () {
                    var $option = $(this);
                    if (classes.indexOf($option.val()) !== -1) {
                        $option.attr("checked", "checked");
                    }
                });
            }

            var match, $control;
            if (href && (match = /mailto:(.+)/.exec(href))) {
                this.$('input.email-address').val(match[1]).change();
            }
            if (href && !$control) {
                this.page_exists(href).then(function (exist) {
                    if (exist) {
                        self.$('#link-page').select2('data', {'id': href, 'text': href});
                    } else {
                        self.$('input.url').val(href).change();
                        self.$('input.window-new').closest("div").show();
                    }
                });
            }

            this.page_exists(href).then(function (exist) {
                if (exist) {
                    self.$('#link-page').select2('data', {'id': href, 'text': href});
                } else {
                    self.$('input.url').val(href).change();
                    self.$('input.window-new').closest("div").show();
                }
            });

            this.preview();
        },
        changed: function (e) {
            var $e = $(e.target);
            this.$('.url-source').filter(':input').not($e).val('')
                    .filter(function () { return !!$(this).data('select2'); })
                    .select2('data', null);
            $e.closest('.list-group-item')
                .addClass('active')
                .siblings().removeClass('active')
                .addBack().removeClass('has-error');
            this.preview();
        },
        call: function (method, args, kwargs) {
            var self = this;
            var req = method + '_req';
            if (this[req]) { this[req].abort(); }
            return this[req] = openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: method,
                args: args,
                kwargs: kwargs,
            }).always(function () {
                self[req] = null;
            });
        },
        page_exists: function (term) {
            return this.call('page_exists', [null, term], {
                context: website.get_context(),
            });
        },
        fetch_pages: function (term) {
            return this.call('search_pages', [null, term], {
                limit: 9,
                context: website.get_context(),
            });
        },
        onkeyup: function (e) {
            var $e = $(e.target);
            var is_link = ($e.val()||'').length && $e.val().indexOf("@") === -1;
            this.$('input.window-new').closest("div").toggle(is_link);
            this.preview();
        },
        preview: function () {
            var $preview = this.$("#link-preview");
            this.get_data(true).then(function (url, new_window, label, classes) {
                $preview.attr("target", new_window ? '_blank' : "")
                    .attr("href", url && url.length ? url : "#")
                    .html((label && label.length ? label : url))
                    .attr("class", classes.replace(/pull-\w+/, ''));
            });
        }
    });

    /**
     * alt widget. Lets users change a alt & title on a media
     */
    website.editor.alt = website.editor.Dialog.extend({
        template: 'website.editor.dialog.alt',
        init: function ($editable, media) {
            this.$editable = $editable;
            this.media = media;
            this.alt = ($(this.media).attr('alt') || "").replace(/&quot;/g, '"');
            this.title = ($(this.media).attr('title') || "").replace(/&quot;/g, '"');
            return this._super();
        },
        save: function () {
            var self = this;
            range.createFromNode(self.media).select();
            this.$editable.data('NoteHistory').recordUndo();
            var alt = this.$('#alt').val();
            var title = this.$('#title').val();
            $(this.media).attr('alt', alt ? alt.replace(/"/g, "&quot;") : null).attr('title', title ? title.replace(/"/g, "&quot;") : null);
            setTimeout(function () {
                click_event(self.media, "mouseup");
            },0);
            return this._super();
        },
    });

    var click_event = function(el, type) {
        var evt = document.createEvent("MouseEvents");
        evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(evt);
    };

    /**
     * MediaDialog widget. Lets users change a media, including uploading a
     * new image, font awsome or video and can change a media into an other
     * media
     *
     * options: select_images: allow the selection of more of one image
     */
    website.editor.MediaDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.media',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            'input input#icon-search': 'search',
        }),
        init: function ($editable, media, options) {
            this._super();
            if ($editable) {
                this.$editable = $editable;
                this.rte = this.$editable.rte || this.$editable.data('rte');
            }
            this.options = options || {};
            this.old_media = media;
            this.media = media;
            this.isNewMedia = !media;
            this.range = range.create();
        },
        start: function () {
            var self = this;

            this.only_images = this.options.only_images || this.options.select_images || (this.media && $(this.media).parent().data("oe-field") === "image");
            if (this.only_images) {
                this.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
            }

            if (this.media) {
                if (this.media.nodeName === "IMG") {
                    this.$('[href="#editor-media-image"]').tab('show');
                } else if (this.media.className.match(/(^|\s)media_iframe_video($|\s)/)) {
                    this.$('[href="#editor-media-video"]').tab('show');
                }  else if (this.media.parentNode.className.match(/(^|\s)media_iframe_video($|\s)/)) {
                    this.media = this.media.parentNode;
                    this.$('[href="#editor-media-video"]').tab('show');
                } else if (this.media.className.match(/(^|\s)fa($|\s)/)) {
                    this.$('[href="#editor-media-icon"]').tab('show');
                }
            }

            this.imageDialog = new website.editor.ImageDialog(this, this.media, this.options);
            this.imageDialog.appendTo(this.$("#editor-media-image"));
            this.iconDialog = new website.editor.FontIconsDialog(this, this.media, this.options);
            this.iconDialog.appendTo(this.$("#editor-media-icon"));
            this.videoDialog = new website.editor.VideoDialog(this, this.media, this.options);
            this.videoDialog.appendTo(this.$("#editor-media-video"));

            this.active = this.imageDialog;

            $('a[data-toggle="tab"]').on('shown.bs.tab', function (event) {
                if ($(event.target).is('[href="#editor-media-image"]')) {
                    self.active = self.imageDialog;
                    self.$('li.search, li.previous, li.next').removeClass("hidden");
                } else if ($(event.target).is('[href="#editor-media-icon"]')) {
                    self.active = self.iconDialog;
                    self.$('li.search, li.previous, li.next').removeClass("hidden");
                    self.$('.nav-tabs li.previous, .nav-tabs li.next').addClass("hidden");
                } else if ($(event.target).is('[href="#editor-media-video"]')) {
                    self.active = self.videoDialog;
                    self.$('.nav-tabs li.search').addClass("hidden");
                }
            });

            return this._super();
        },
        save: function () {
            if (this.options.select_images) {
                this.trigger("saved", this.active.save());
                this.close();
                return;
            }
            if(this.rte) {
                this.range.select();
                this.rte.historyRecordUndo(this.media);
            }

            var self = this;
            if (self.media) {
                this.media.innerHTML = "";
                if (this.active !== this.imageDialog) {
                    this.imageDialog.clear();
                }
                if (this.active !== this.iconDialog) {
                    this.iconDialog.clear();
                }
                if (this.active !== this.videoDialog) {
                    this.videoDialog.clear();
                }
            } else {
                this.media = document.createElement("img");
                this.range.insertNode(this.media, true);
                this.active.media = this.media;
            }
            this.active.save();

            if (this.active.add_class) {
                $(this.media).addClass(this.active.add_class);
            }

            $(document.body).trigger("media-saved", [self.active.media, self.old_media]);
            self.trigger("saved", [self.active.media, self.old_media]);
            setTimeout(function () {
                if (!self.active.media.parentNode) {
                    return;
                }
                range.createFromNode(self.active.media).select();
                click_event(self.active.media, "mousedown");
                if (!this.only_images) {
                    setTimeout(function () {
                        if($(self.active.media).parent().data("oe-field") !== "image") {
                            click_event(self.active.media, "click");
                        }
                        click_event(self.active.media, "mouseup");
                    },0);
                }
            },0);

            this.close();
        },
        searchTimer: null,
        search: function () {
            var self = this;
            var needle = this.$("input#icon-search").val();
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(function () {
                self.active.search(needle || "");
            },250);
        }
    });

    /**
     * ImageDialog widget. Lets users change an image, including uploading a
     * new image in OpenERP or selecting the image style (if supported by
     * the caller).
     */
    var IMAGES_PER_ROW = 6;
    var IMAGES_ROWS = 2;
    website.editor.ImageDialog = openerp.Widget.extend({
        template: 'website.editor.dialog.image',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .url-source': function (e) {
                this.changed($(e.target));
            },
            'click button.filepicker': function () {
                var filepicker = this.$('input[type=file]');
                if (!_.isEmpty(filepicker)){
                    filepicker[0].click();
                }
            },
            'click .js_disable_optimization': function () {
                this.$('input[name="disable_optimization"]').val('1');
                var filepicker = this.$('button.filepicker');
                if (!_.isEmpty(filepicker)){
                    filepicker[0].click();
                }
            },
            'change input[type=file]': 'file_selection',
            'submit form': 'form_submit',
            'change input.url': "change_input",
            'keyup input.url': "change_input",
            //'change select.image-style': 'preview_image',
            'click .existing-attachments img': 'select_existing',
            'click .existing-attachment-remove': 'try_remove',
        }),
        init: function (parent, media, options) {
            this._super();
            this.options = options || {};
            this.parent = parent;
            this.media = media;
            this.images = [];
            this.page = 0;
        },
        start: function () {
            this.$preview = this.$('.preview-container').detach();
            var self = this;
            var res = this._super();
            var o = { url: null, alt: null };
            // avoid typos, prevent addition of new properties to the object
            Object.preventExtensions(o);

            if ($(this.media).is("img")) {
                o.url = this.media.getAttribute('src');
            } else {
                this.add_class = "img-responsive pull-left";
            }
            this.parent.$(".pager > li").click(function (e) {
                e.preventDefault();
                var $target = $(e.currentTarget);
                if ($target.hasClass('disabled')) {
                    return;
                }
                self.page += $target.hasClass('previous') ? -1 : 1;
                self.display_attachments();
            });
            this.set_image(o.url, o.alt);
            this.fetch_existing();
            return res;
        },
        push: function (url, alt, id) {
            if (this.options.select_images) {
                var img = _.select(this.images, function (v) { return v.url == url;});
                if (img.length) {
                    this.images.splice(this.images.indexOf(img[0]),1);
                    return;
                }
            } else {
                this.images = [];
            }
            this.images.push({'url': url, 'alt': alt, 'id': id});
        },
        save: function () {
            if (this.options.select_images) {
                this.parent.trigger("save", this.images);
                return this.images;
            }
            this.parent.trigger("save", this.media);

            var img = this.images[0] || {
                    'url': this.$(".existing-attachments img:first").attr('src'),
                    'alt': this.$(".existing-attachments img:first").attr('alt')
                };

            if (this.media.tagName !== "IMG") {
                var media = document.createElement('img');
                $(this.media).replaceWith(media);
                this.media = media;
            }

            $(this.media).attr('src', img.url).attr('alt', img.alt);

            var style = this.style;
            this.media.setAttribute('src', img.url);
            if (style) { this.media.addClass(style); }

            return this.media;
        },
        clear: function () {
            this.media.className = this.media.className.replace(/(^|\s)(img(\s|$)|img-[^\s]*)/g, ' ');
        },
        cancel: function () {
            this.trigger('cancel');
        },
        change_input: function (e) {
            var $input = $(e.target);
            var $button = $input.parent().find("button");
            if ($input.val() === "") {
                $button.addClass("btn-default").removeClass("btn-primary");
            } else {
                $button.removeClass("btn-default").addClass("btn-primary");
            }
        },
        search: function (needle) {
            var self = this;
            this.fetch_existing(needle).then(function () {
                self.selected_existing();
            });
        },
        set_image: function (url, alt, error) {
            var self = this;
            if (url) {
                this.push(url, alt);
            }
            this.$('input.url').val('');
            this.fetch_existing().then(function () {
                self.selected_existing();
            });
        },
        form_submit: function (event) {
            var self = this;
            var $form = this.$('form[action="/website/attach"]');
            if (!$form.find('input[name="upload"]').val().length) {
                var url = $form.find('input[name="url"]').val();
                if (this.selected_existing().size()) {
                    event.preventDefault();
                    return false;
                }
            }
            $form.find('.well > div').hide().last().after('<span class="fa fa-spin fa-3x fa-refresh"/>');

            var callback = _.uniqueId('func_');
            this.$('input[name=func]').val(callback);
            window[callback] = function (attachments, error) {
                delete window[callback];
                $form.find('.well > span').remove();
                $form.find('.well > div').show();
                if (error || !attachments.length) {
                    self.file_selected(null, error || !attachments.length);
                }
                for (var i=0; i<attachments.length; i++) {
                    self.file_selected(attachments[i]['website_url'], error);
                }
            };
        },
        file_selection: function () {
            this.$el.addClass('nosave');
            this.$('form').removeClass('has-error').find('.help-block').empty();
            this.$('button.filepicker').removeClass('btn-danger btn-success');
            this.$('form').submit();
        },
        file_selected: function(url, error) {
            var $button = this.$('button.filepicker');
            if (!error) {
                $button.addClass('btn-success');
            } else {
                url = null;
                this.$('form').addClass('has-error')
                    .find('.help-block').text(error);
                $button.addClass('btn-danger');
            }
            this.set_image(url, null, error);

            if (!this.options.select_images) {
                // auto save and close popup
                this.parent.save();
            }
        },
        fetch_existing: function (needle) {
            var domain = [['res_model', '=', 'ir.ui.view'], '|',
                        ['mimetype', '=', false], ['mimetype', '=like', 'image/%']];
            if (needle && needle.length) {
                domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
            }
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'search_read',
                args: [],
                kwargs: {
                    domain: domain,
                    fields: ['name', 'website_url'],
                    order: 'id desc',
                    context: website.get_context()
                }
            }).then(this.proxy('fetched_existing'));
        },
        fetched_existing: function (records) {
            this.records = records;
            this.display_attachments();
        },
        display_attachments: function () {
            this.$('.help-block').empty();
            var per_screen = IMAGES_PER_ROW * IMAGES_ROWS;

            var from = this.page * per_screen;
            var records = this.records;

            // Create rows of 3 records
            var rows = _(records).chain()
                .slice(from, from + per_screen)
                .groupBy(function (_, index) { return Math.floor(index / IMAGES_PER_ROW); })
                .values()
                .value();
            this.$('.existing-attachments').replaceWith(
                openerp.qweb.render(
                    'website.editor.dialog.image.existing.content', {rows: rows}));
            this.parent.$('.pager')
                .find('li.previous').toggleClass('disabled', (from === 0)).end()
                .find('li.next').toggleClass('disabled', (from + per_screen >= records.length));

            this.selected_existing();
        },
        select_existing: function (e) {
            var $img = $(e.currentTarget);
            this.push($img.attr('src'), $img.attr('alt'), $img.data('id'));
            this.selected_existing();
        },
        selected_existing: function () {
            var self = this;
            this.$('.existing-attachment-cell.media_selected').removeClass("media_selected");
            var $select = this.$('.existing-attachment-cell img').filter(function () {
                var $img = $(this);
                var url = $img.attr("src");
                return !!_.select(self.images, function (v) {
                    if (v.url === url) {
                        if (!v.id) {
                            v.id = $img.data('id');
                            v.alt = $img.attr('alt');
                        }
                        return true;
                    }
                }).length;
            });
            $select.parent().addClass("media_selected");
            return $select;
        },
        try_remove: function (e) {
            var $help_block = this.$('.help-block').empty();
            var self = this;
            var $a = $(e.target);
            var id = parseInt($a.data('id'), 10);
            var attachment = _.findWhere(this.records, {id: id});
            var $both = $a.parent().children();

            $both.css({borderWidth: "5px", borderColor: "#f00"});

            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'try_remove',
                args: [],
                kwargs: {
                    ids: [id],
                    context: website.get_context()
                }
            }).then(function (prevented) {
                if (_.isEmpty(prevented)) {
                    self.records = _.without(self.records, attachment);
                    self.display_attachments();
                    return;
                }
                $both.css({borderWidth: "", borderColor: ""});
                $help_block.replaceWith(openerp.qweb.render(
                    'website.editor.dialog.image.existing.error', {
                        views: prevented[id]
                    }
                ));
            });
        },
    });


    var cacheCssSelectors = {};
    website.editor.getCssSelectors = function(filter) {
        var css = [];
        if (cacheCssSelectors[filter]) {
            return cacheCssSelectors[filter];
        }
        var sheets = document.styleSheets;
        for(var i = 0; i < sheets.length; i++) {
            try {
                var rules = sheets[i].rules || sheets[i].cssRules;
            } catch(e) {
                continue;
            }
            if (rules) {
                for(var r = 0; r < rules.length; r++) {
                    var selectorText = rules[r].selectorText;
                    if (selectorText) {
                        var match = selectorText.match(filter);
                        if (match) {
                            css.push([match[1], rules[r].cssText.replace(/(^.*\{\s*)|(\s*\}\s*$)/g, '')]);
                        }
                    }
                }
            }
        }
        return cacheCssSelectors[filter] = css;
    };
    function computeFonts() {
        _.each(website.editor.fontIcons, function (data) {
            data.icons = _.map(website.editor.getCssSelectors(data.parser), function (css) {
                return css[0].slice(1, css[0].length).replace(/::?before$/, '');
            });
        });
    }

    /* list of font icons to load by editor. The icons are displayed in the media editor and
     * identified like font and image (can be colored, spinned, resized with fa classes).
     * To add font, push a new object {base, parser}
     * - base: class who appear on all fonts (eg: fa fa-refresh)
     * - parser: regular expression used to select all font in css style sheets
     */
    website.editor.fontIcons = [{'base': 'fa', 'parser': /(?=^|\s)(\.fa-[0-9a-z_-]+::?before)/i}];


    /**
     * FontIconsDialog widget. Lets users change a font awsome, suport all
     * font awsome loaded in the css files.
     */
    website.editor.FontIconsDialog = openerp.Widget.extend({
        template: 'website.editor.dialog.font-icons',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            'click .font-icons-icon': function (e) {
                e.preventDefault();
                e.stopPropagation();

                this.$('#fa-icon').val(e.target.getAttribute('data-id'));
                $(".font-icons-icon").removeClass("font-icons-selected");
                $(event.target).addClass("font-icons-selected");
            },
        }),

        // extract list of font (like awsome) from the cheatsheet.
        renderElement: function() {
            this.iconsParser = website.editor.fontIcons;
            this.icons = _.flatten(_.map(website.editor.fontIcons, function (data) {
                    return data.icons;
                }));
            this._super();
        },

        init: function (parent, media) {
            this._super();
            this.parent = parent;
            this.media = media;
        },
        start: function () {
            return this._super().then(this.proxy('load_data'));
        },
        search: function (needle) {
            var iconsParser = this.iconsParser;
            if (needle) {
                var parser = [];
                var fontIcons = website.editor.fontIcons, fontIcon;

                for (var k=0; k<fontIcons.length; k++) {
                    fontIcon = fontIcons[k];
                    var icons = _(fontIcon.icons).filter(function (icon) {
                        return icon.indexOf(needle) !== -1;
                    });
                    if (icons.length) {
                        parser.push({
                            base: fontIcon.base,
                            icons: icons
                        });
                    }
                }
                iconsParser = parser;
            }
            this.$('div.font-icons-icons').html(
                openerp.qweb.render('website.editor.dialog.font-icons.icons', {'iconsParser': iconsParser}));
        },
        /**
         * Removes existing FontAwesome classes on the bound element, and sets
         * all the new ones if necessary.
         */
        save: function () {
            var self = this;
            this.parent.trigger("save", this.media);
            var icons = this.icons;
            var style = this.media.attributes.style ? this.media.attributes.style.value : '';
            var classes = (this.media.className||"").split(/\s+/);
            var non_fa_classes = _.reject(classes, function (cls) {
                return self.getFont(cls);
            });
            var final_classes = non_fa_classes.concat(this.get_fa_classes());
            if (this.media.tagName !== "SPAN") {
                var media = document.createElement('span');
                $(this.media).replaceWith(media);
                this.media = media;
                style = style.replace(/\s*width:[^;]+/, '');
            }
            $(this.media).attr("class", _.compact(final_classes).join(' ')).attr("style", style);
        },
        /**
         * return the data font object (with base, parser and icons) or null
         */
        getFont: function (classNames) {
            if (!(classNames instanceof Array)) {
                classNames = (classNames||"").split(/\s+/);
            }
            var fontIcons = website.editor.fontIcons, fontIcon, className;
            for (var i=0; i<classNames.length; i++) {
                className = classNames[i];
                for (var k=0; k<fontIcons.length; k++) {
                    fontIcon = fontIcons[k];
                    if (className === fontIcon.base || fontIcon.icons.indexOf(className) !== -1) {
                        return {
                            'base': fontIcon.base,
                            'parser': fontIcon.parser,
                            'icons': fontIcon.icons,
                            'font': className
                        };
                    }
                }
            }
            return null;
        },

        /**
         * Looks up the various FontAwesome classes on the bound element and
         * sets the corresponding template/form elements to the right state.
         * If multiple classes of the same category are present on an element
         * (e.g. fa-lg and fa-3x) the last one occurring will be selected,
         * which may not match the visual look of the element.
         */
        load_data: function () {
            var classes = (this.media&&this.media.className||"").split(/\s+/);
            for (var i = 0; i < classes.length; i++) {
                var cls = classes[i];
                switch(cls) {
                    case 'fa-1x':case 'fa-2x':case 'fa-3x':case 'fa-4x':case 'fa-5x':
                        // size classes
                        this.$('#fa-size').val(cls);
                        continue;
                    case 'fa-spin':
                    case 'fa-rotate-90':case 'fa-rotate-180':case 'fa-rotate-270':
                    case 'fa-flip-horizontal':case 'fa-rotate-vertical':
                        this.$('#fa-rotation').val(cls);
                        continue;
                    case 'fa-fw':
                        continue;
                    case 'fa-border':
                        this.$('#fa-border').prop('checked', true);
                        continue;
                    case '': continue;
                    default:
                        $(".font-icons-icon").removeClass("font-icons-selected").filter("."+cls).addClass("font-icons-selected");
                        for (var k=0; k<this.icons.length; k++) {
                            if (this.icons.indexOf(cls) !== -1) {
                                this.$('#fa-icon').val(cls);
                                break;
                            }
                        }
                }
            }
        },
        /**
         * Serializes the dialog to an array of FontAwesome classes. Includes
         * the base ``fa``.
         */
        get_fa_classes: function () {
            var font = this.getFont(this.$('#fa-icon').val());
            return [
                font ? font.base : 'fa',
                font ? font.font : "",
                this.$('#fa-size').val(),
                this.$('#fa-rotation').val(),
                this.$('#fa-border').prop('checked') ? 'fa-border' : ''
            ];
        },
        clear: function () {
            this.media.className = this.media.className.replace(/(^|\s)(fa(\s|$)|fa-[^\s]*)/g, ' ');
        },
    });


    function createVideoNode(url) {
        // video url patterns(youtube, instagram, vimeo, dailymotion, youku)
        var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
        var ytMatch = url.match(ytRegExp);

        var igRegExp = /\/\/instagram.com\/p\/(.[a-zA-Z0-9]*)/;
        var igMatch = url.match(igRegExp);

        var vRegExp = /\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/;
        var vMatch = url.match(vRegExp);

        var vimRegExp = /\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/;
        var vimMatch = url.match(vimRegExp);

        var dmRegExp = /.+dailymotion.com\/(video|hub)\/([^_]+)[^#]*(#video=([^_&]+))?/;
        var dmMatch = url.match(dmRegExp);

        var youkuRegExp = /\/\/v\.youku\.com\/v_show\/id_(\w+)\.html/;
        var youkuMatch = url.match(youkuRegExp);

        var $video = $('<iframe>');
        if (ytMatch && ytMatch[1].length === 11) {
          var youtubeId = ytMatch[1];
          $video = $('<iframe>')
            .attr('src', '//www.youtube.com/embed/' + youtubeId)
            .attr('width', '640').attr('height', '360');
        } else if (igMatch && igMatch[0].length) {
          $video = $('<iframe>')
            .attr('src', igMatch[0] + '/embed/')
            .attr('width', '612').attr('height', '710')
            .attr('scrolling', 'no')
            .attr('allowtransparency', 'true');
        } else if (vMatch && vMatch[0].length) {
          $video = $('<iframe>')
            .attr('src', vMatch[0] + '/embed/simple')
            .attr('width', '600').attr('height', '600')
            .attr('class', 'vine-embed');
        } else if (vimMatch && vimMatch[3].length) {
          $video = $('<iframe webkitallowfullscreen mozallowfullscreen allowfullscreen>')
            .attr('src', '//player.vimeo.com/video/' + vimMatch[3])
            .attr('width', '640').attr('height', '360');
        } else if (dmMatch && dmMatch[2].length) {
          $video = $('<iframe>')
            .attr('src', '//www.dailymotion.com/embed/video/' + dmMatch[2])
            .attr('width', '640').attr('height', '360');
        } else if (youkuMatch && youkuMatch[1].length) {
          $video = $('<iframe webkitallowfullscreen mozallowfullscreen allowfullscreen>')
            .attr('height', '498')
            .attr('width', '510')
            .attr('src', '//player.youku.com/embed/' + youkuMatch[1]);
        } else {
          // this is not a known video link. Now what, Cat? Now what?
        }

        $video.attr('frameborder', 0);

        return $video;
      };

    /**
     * VideoDialog widget. Lets users change a video, support all summernote
     * video, and embled iframe
     */
    website.editor.VideoDialog = openerp.Widget.extend({
        template: 'website.editor.dialog.video',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            'click input#urlvideo ~ button': 'get_video',
            'click input#embedvideo ~ button': 'get_embed_video',
            'change input#urlvideo': 'change_input',
            'keyup input#urlvideo': 'change_input',
            'change input#embedvideo': 'change_input',
            'keyup input#embedvideo': 'change_input'
        }),
        init: function (parent, media) {
            this._super();
            this.parent = parent;
            this.media = media;
        },
        start: function () {
            this.$preview = this.$('.preview-container').detach();
            this.$iframe = this.$("iframe");
            var $media = $(this.media);
            if ($media.hasClass("media_iframe_video")) {
                var src = $media.data('src');
                this.$("input#urlvideo").val(src);
                this.$("#autoplay").attr("checked", src.indexOf('autoplay=1') != -1);
                this.get_video();
            } else {
                this.add_class = "pull-left";
            }
            return this._super();
        },
        change_input: function (e) {
            var $input = $(e.target);
            var $button = $input.parent().find("button");
            if ($input.val() === "") {
                $button.addClass("btn-default").removeClass("btn-primary");
            } else {
                $button.removeClass("btn-default").addClass("btn-primary");
            }
        },
        get_embed_video: function (event) {
            event.preventDefault();
            var embedvideo = this.$("input#embedvideo").val().match(/src=["']?([^"']+)["' ]?/);
            if (embedvideo) {
                this.$("input#urlvideo").val(embedvideo[1]);
                this.get_video(event);
            }
            return false;
        },
        get_video: function (event) {
            if (event) event.preventDefault();
            var $video = createVideoNode(this.$("input#urlvideo").val());
            this.$iframe.replaceWith($video);
            this.$iframe = $video;
            return false;
        },
        save: function () {
            this.parent.trigger("save", this.media);
            var video_id = this.$("#video_id").val();
            if (!video_id) {
                this.$("button.btn-primary").click();
                video_id = this.$("#video_id").val();
            }
            var video_type = this.$("#video_type").val();
            var $iframe = $(
                '<div class="media_iframe_video" data-src="'+this.$iframe.attr("src")+'">'+
                    '<div class="css_editable_mode_display">&nbsp;</div>'+
                    '<div class="media_iframe_video_size" contentEditable="false">&nbsp;</div>'+
                    '<iframe src="'+this.$iframe.attr("src")+'" frameborder="0" allowfullscreen="allowfullscreen" contentEditable="false"></iframe>'+
                '</div>');
            $(this.media).replaceWith($iframe);
            this.media = $iframe[0];
        },
        clear: function () {
            delete this.media.dataset.src;
            this.media.className = this.media.className.replace(/(^|\s)media_iframe_video(\s|$)/g, ' ');
        },
    });

});

openerp.define.desactive();

})();

