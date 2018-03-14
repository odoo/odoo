odoo.define('web_editor.tour', function (require) {
'use strict';

var core = require('web.core');
var tour = require('web_tour.tour');
var base = require('web_editor.base');

/**
 * Simulates a click event of given type on the given element.
 *
 * @param {DOMElement} el
 * @param {string} type - 'click', 'mouseup', ...
 */
function simulateClickEvent(el, type) {
    var evt = document.createEvent('MouseEvents');
    evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
    el.dispatchEvent(evt);
}

tour.register('rte', {
    url: '/web_editor/field/html?callback=FieldTextHtml_0&enable_editor=1&datarecord=%7B%7D',
    test: true,
    wait_for: base.ready(),
}, [{
    content: "Change html for this test",
    trigger: "#editable_area",
    run: function () {
        var html = '\n'+
            '<section>\n'+
            '    <div class="container" style="width: 600px;">\n'+
            '        <div class="row">\n'+
            '            <div class="col-md-6 mt16">\n'+
            '<h1 id="text_content_id">Batnae municipium in Anthemusia</h1>     \n'+
            '     <p>Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab Euphrate flumine brevi spatio disparatur, refertum mercatoribus opulentis, ubi annua sollemnitate prope Septembris initium mensis ad.</p>\n'+
            '     <p>    Quam <img style="width: 25%" src="/web/static/src/img/logo.png"/> quidem <span class="fa fa-flag fa-2x"></span> partem accusationis admiratus sum et moleste tuli potissimum esse Atratino datam. Neque enim decebat neque aetas.</p>\n'+
            '     <p>Et hanc quidem praeter oppida multa duae civitates exornant Seleucia opus Seleuci regis, et Claudiopolis quam deduxit coloniam Claudius Caesar. Isaura enim antehac nimium potens, olim subversa ut rebellatrix.</p>'+
            '<p>Harum trium sententiarum nulli prorsus assentior.</p>\n'+
            '        </div>\n'+
            '        <div class="col-md-6 mt16">\n'+
            '            <img class="img img-responsive shadow mb16" src="/web/static/src/img/logo.png" alt="Odoo text and image block">\n'+
            '        </div>\n'+
            '    </div>\n'+
            '</section>\n';
        this.$anchor.html(html);
    }
}, {
    content: "simulate triple click and change text bg-color",
    trigger: '#editable_area > section .row > div:first',
    run: function () {
        var $h1 = $('h1', this.$anchor);
        $.summernote.core.range.create($h1[0].firstChild, 0, $('p', this.$anchor)[0], 0).select();
        simulateClickEvent($h1[0], 'mouseup');
    }
}, {
    content: "change text bg-color after triple click",
    trigger: '.note-popover button[data-event="color"]',
    extra_trigger: '#editable_area > section .row > div:first',
}, {
    content: "change selection to change text color",
    trigger: '#editable_area > section .row > div:first:not(:has(p font)) h1 font',
    run: function () {
        $.summernote.core.range.create(this.$anchor[0].firstChild, 5, this.$anchor[0].firstChild, 10).select();
        simulateClickEvent(this.$anchor[0], 'mouseup');
    }
}, {
    content: "open color dropdown",
    trigger: ".note-color button.dropdown-toggle",
}, {
    content: "change text color",
    trigger: ".btn-group.open button[data-event=foreColor]:first",
}, {
    content: "change selection to change text bg-color again",
    trigger: '#editable_area > section .row > div:first h1 font:eq(2)',
    run: function () {
        $.summernote.core.range.create(this.$anchor.prev()[0].firstChild, 3, this.$anchor[0].firstChild, 10).select();
        simulateClickEvent(this.$anchor.prev()[0], 'mouseup');
    }
}, {
    content: "open color dropdown",
    trigger: ".note-color button.dropdown-toggle",
}, {
    content: "change text backColor again",
    trigger: "button[data-event=backColor]:visible:first",
}, {
    content: "change selection (h1 and p) to change text color with class",
    trigger: '#editable_area > section .row > div:first h1 font:eq(4)',
    run: function () {
        $.summernote.core.range.create(this.$anchor.prev()[0].firstChild, 3, this.$anchor.parent("h1").next("p")[0].firstChild, 30).select();
        simulateClickEvent(this.$anchor.prev()[0], 'mouseup');
    }
}, {
    content: "open color dropdown",
    trigger: ".note-color button.dropdown-toggle",
}, {
    content: "change text color again",
    trigger: "button[data-event=foreColor]:visible:eq(3)",
}, {
    content: "delete selection",
    trigger: '.o_editable.note-editable.o_dirty',
    extra_trigger: '#editable_area > section .row > div:first p font',
    run: "keydown 46", // delete
}, {
    content: "create an other selection to delete",
    trigger: '#editable_area > section .row > div:first:not(:has(p font)) h1',
    extra_trigger: '.o_editable.note-editable.o_dirty',
    run: function () {
        $.summernote.core.range.createFromNode(this.$anchor.next("p")[0]).clean();
        $.summernote.core.range.create(this.$anchor.find('font:containsExact(ici)')[0].firstChild, 1, this.$anchor.next().next()[0].firstChild, 5).select();
        simulateClickEvent(this.$anchor.find('font:last')[0], 'mouseup');
    },
}, {
    content: "clean and delete (backspace) an other selection",
    trigger: '#editable_area > section .row > div:first:not(:has(p font)) h1',
    run: "keydown 8", // backspace
}, {
    content: "an other selection",
    trigger: '#editable_area > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) ) h1',
    extra_trigger: '.o_editable.note-editable.o_dirty',
    run: function () {
        $.summernote.core.range.create(this.$anchor.find('font:first')[0].firstChild, 3, this.$anchor.next("p")[0].childNodes[2], 8).select();
        simulateClickEvent(this.$anchor.find('font:first')[0], 'mouseup');
    },
}, {
    content: "delete an other selection",
    trigger: '#editable_area > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) ) h1',
    run: "keydown 46",
}, {
    content: "undo",
    trigger: '.note-image-popover button[data-event="undo"]',
    extra_trigger: '#editable_area > section .row > div:first:has( font:last:containsExact(Bat) )',
}, {
    content: "undo again",
    trigger: '.note-air-popover button[data-event="undo"]',
    extra_trigger: '#editable_area > section .row > div:first:has( font:last:containsExact(i) )',
}, {
    content: "delete (backspace) after undo",
    trigger: '.o_editable.note-editable.o_dirty',
    extra_trigger: '#editable_area > section .row > div:first:not(:has(p font)) h1',
    run: "keydown 8", // backspace
}, {
    content: "click on image",
    trigger: '#editable_area > section .row > div:first img[style*="25%"]',
    extra_trigger: '#editable_area > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) )',
}, {
    content: "Click on resize half",
    trigger: '.note-image-popover:visible button[data-event="resize"][data-value="0.5"]',
}, {
    content: "Click on edit picture",
    trigger: '.note-image-popover:visible button[data-event="showImageDialog"]',
    extra_trigger: '#editable_area > section .row > div:first img[style*="50%"]',
}, {
    content: "Click on pictogram tab",
    trigger: 'a[data-toggle="tab"]:contains(Pictogram)',
    extra_trigger: '#editor-media-image',
}, {
    content: "select a pictogram",
    trigger: '#editor-media-icon.active span.fa:first',
}, {
    content: "save pictogram",
    trigger: '.modal-footer > .btn-primary',
    extra_trigger: '#editor-media-icon.active span.o_selected',
}, {
    content: "select a size for the pictogram",
    trigger: '.note-image-popover button[data-event="resizefa"][data-value="3"]',
}, {
    content: "click on float right",
    trigger: '.note-image-popover:visible button[data-event="floatMe"][data-value="right"]',
    extra_trigger: '#wrapwrap span.fa-3x',
}, {
    content: "click on create link",
    trigger: '.note-image-popover:visible button[data-event="showLinkDialog"]',
    extra_trigger: '#editable_area > section .row > div:first span.fa.pull-right',
}, {
    content: "insert a link url",
    trigger: 'input[name="url"]',
    run: "text http://www.odoo.com",
}, {
    content: "click on color style",
    trigger: '.o_link_dialog_color > .o_link_dialog_color_item.btn-success',
    extra_trigger: 'a#link-preview:containsRegex(/^<span [^>]+><\\/span>$/) > span.fa.fa-3x.pull-right',
}, {
    content: "save link",
    trigger: '.modal-footer > .btn-primary',
    extra_trigger: 'a#link-preview.btn.btn-success:containsRegex(/^<span [^>]+><\\/span>$/) > span.fa.fa-3x.pull-right',
}, {
    content: "click on other picture",
    trigger: '#editable_area > section .row > div:last img',
    extra_trigger: 'body:not(:has(#link-preview)) a.btn[href^="http://"]:has(span.fa.fa-3x.pull-right)',
}, {
    content: "click on create link again",
    trigger: '.note-image-popover:visible button[data-event="showLinkDialog"]',
    extra_trigger: '#editable_area > section .row > div:first span.fa.pull-right',
}, {
    content: "insert an email",
    trigger: 'input[name="url"]',
    run: "text test@test.test",
}, {
    content: "click on color style again",
    trigger: '.o_link_dialog_color > .o_link_dialog_color_item.btn-success',
    extra_trigger: 'a#link-preview:containsRegex(/^<img [^>]+>$/) img',
}, {
    content: "save link",
    trigger: '.modal-footer > .btn-primary',
    extra_trigger: 'a#link-preview.btn.btn-success[href="mailto:test@test.test"]:containsRegex(/^<img [^>]+>$/) img',
}, {
    content: "select for triple enter then double backspace",
    trigger: '#editable_area > section .row > div:first p:eq(2)',
    extra_trigger: 'body:not(:has(#link-preview)) #editable_area > section .row > div:eq(1) > a > img',
    run: function () {
        var p = this.$anchor[0].firstChild;
        $.summernote.core.range.create(p, p.textContent.length, p, p.textContent.length).select();
        simulateClickEvent(p, 'mouseup');
    },
}, {
    content: "triple enter then double backspace",
    trigger: '#editable_area > section .row > div:first p:eq(2)',
    run: "keydown 66,13,66,13,13,8,8", // B enter B enter enter backspace backspace
}, {
    content: "add ul content",
    trigger: '#editable_area > section .row > div:first',
    extra_trigger: 'body:not(:has(#editable_area > section .row > div:first p:eq(5), #editable_area > section .row > div:eq(3))) #editable_area > section .row > div:first p:eq(3)',
    run: function () {
        var html = '  <ul>     '+
            '\n     <li>   <p>Batnae municipium.  </p></li>'+
            '\n     <li>    Seleucia praeter.</li>'+
            '\n     <li><p>Et hanc quidem.</p></li>'+
            '\n    </ul>';
        this.$anchor.append(html);
        var node = this.$anchor.find('ul li p:last')[0].firstChild;
        $.summernote.core.range.create(node, 6).select();
        simulateClickEvent(node, 'mouseup');
    }
}, {
    content: "click on style dropdown",
    trigger: '.note-air-popover .note-style button.dropdown-toggle',
    extra_trigger: '#editable_area > section .row > div:first ul li p:first',
}, {
    content: "select h3",
    trigger: '.note-air-popover .note-style ul:visible a[data-value="h3"]',
}, {
    content: "select h3",
    trigger: '#editable_area > section .row > div:first > ul > li > h3',
    run: function () {
        var node = this.$anchor[0].firstChild;
        $.summernote.core.range.create(node, 0).select();
        simulateClickEvent(node, 'mouseup');
    }
}, {
    content: "double tabulation",
    trigger: '#editable_area > section .row > div:first > ul > li > h3',
    run: "keydown 9,9", // tabulation
}, {
    content: "click on order list",
    trigger: '.note-air-popover button[data-event="insertOrderedList"]',
    extra_trigger: '#editable_area > section .row > div:first ul > li > ul > li > ul > li > h3',
}, {
    content: "select for enter in ul",
    trigger: '#editable_area > section .row > div:first ul li > p:last',
    run: function () {
        this.$anchor[0].firstChild.textContent += "";
        $.summernote.core.range.create(this.$anchor[0].firstChild, 7).select();
        simulateClickEvent(this.$anchor[0], 'mouseup');
    }
}, {
    content: "enter in ul",
    trigger: '#editable_area > section .row > div:first ul li > p:last',
    run: "keydown 66,13", // enter
}, {
    trigger: '#editable_area > section .row > div:first ul li > p:eq(1):containsRegex(/^municipium./)',
    content: "backspace in list",
    run: "keydown 8",
}, {
    content: "end",
    trigger: '#editable_area > section .row > div:first ul li p:eq(0):containsRegex(/^Batnae Bmunicipium.$/)',
}]);

tour.register('rte_inline', {
    url: '/web_editor/field/html/inline?callback=FieldTextHtml_0&enable_editor=1&datarecord=%7B%7D',
    test: true,
    wait_for: base.ready(),
}, [{
    content: "Change html for this test",
    trigger: "#editable_area",
    run: function () {
        var html = '\n'+
            '<div>\n'+
            '  <table cellspacing="0" cellpadding="0" width="100%">\n'+
            '    <tbody>\n'+
            '      <tr>\n'+
            '        <td valign="center" width="270">\n'+
            '          <img src="/logo.png" alt="Your Logo" class="img-circle img-thumbnail">\n'+
            '        </td>\n'+
            '        <td valign="center" width="270">\n'+
            '          <a href="https://www.facebook.com/Odoo"><span class="fa fa-facebook-square fa-2x text-primary"></span></a>\n'+
            '          <span style="color: rgb(255, 0, 0);" class="fa fa-4x fa-google-plus-square pull-right"></span>\n'+
            '        </td>\n'+
            '      </tr>\n'+
            '    </tbody>\n'+
            '  </table>\n'+
            '</div>';
        this.$anchor.html(html);
    }
}, {
    content: "call clean for save",
    trigger: '#wrapwrap table',
    run: function () {
        core.bus.trigger('snippet_editor_clean_for_save');
    }
}, {
    content: "check the image style",
    trigger: '#wrapwrap img:first[width][height][style*="-radius"][style*="1px"][style*="padding"]',
}, {
    content: "check the font image src",
    trigger: '#wrapwrap img:eq(1)[src^="/web_editor/font_to_img/"][src$="/rgb(51,122,183)/28"]',
}, {
    content: "check the font class to css",
    trigger: '#wrapwrap img:eq(1)[height]:not([class*="fa"])',
}, {
    content: "check the second font class to css",
    trigger: '#wrapwrap img:eq(2)[style*="float: right"],#wrapwrap img:eq(2)[style*="float:right"]',
}]);
});
