odoo.define('web_editor.tour', function (require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');
var base = require('web_editor.base');
var snippet_editor = require('web_editor.snippet.editor');

var _t = core._t;

base.ready().done(function () {

var click_event = function(el, type) {
    var evt = document.createEvent("MouseEvents");
    evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
    el.dispatchEvent(evt);
};

Tour.register({
    id:   'rte',
    name: "Test RTE",
    mode: 'test',
    path: '/web_editor/field/html?callback=FieldTextHtml_0&enable_editor=1&datarecord=%7B%7D',
    steps: [
        {
            title:     "Change html for this test",
            onload: function () {
                var html = '\n'+
                    '<section>\n'+
                    '    <div class="container">\n'+
                    '        <div class="row">\n'+
                    '            <div class="col-md-6 mt16">\n'+
                    '<h1 id="text_title_id">Batnae municipium in Anthemusia</h1>     \n'+
                    '     <p>Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab Euphrate flumine brevi spatio disparatur, refertum mercatoribus opulentis, ubi annua sollemnitate prope Septembris initium mensis ad.</p>\n'+
                    '     <p>    Quam <img style="width: 25%" src="/web_editor/static/src/img/drag_here.png"/> quidem <span class="fa fa-flag fa-2x"></span> partem accusationis admiratus sum et moleste tuli potissimum esse Atratino datam. Neque enim decebat neque aetas.</p>\n'+
                    '     <p>Et hanc quidem praeter oppida multa duae civitates exornant Seleucia opus Seleuci regis, et Claudiopolis quam deduxit coloniam Claudius Caesar. Isaura enim antehac nimium potens, olim subversa ut rebellatrix.</p>'+
                    '<p>Harum trium sententiarum nulli prorsus assentior.</p>\n'+
                    '        </div>\n'+
                    '        <div class="col-md-6 mt16">\n'+
                    '            <img class="img img-responsive shadow mb16" src="/web_editor/static/src/img/drag_here.png" alt="Odoo text and image block">\n'+
                    '        </div>\n'+
                    '    </div>\n'+
                    '</section>\n';
                $("#editable_area").html(html);
            }
        },
        {
            element:   '#editable_area > section .row > div:first',
            title:     "simulate triple click and change text bg-color",
            onload: function () {
                var $el = $(this.element);
                var $h1 = $('h1', $el);
                $.summernote.core.range.create($h1[0].firstChild, 0, $('p', $el)[0], 0).select();
                click_event($h1[0], 'mouseup');
            }
        },
        {
            waitFor:   '#editable_area > section .row > div:first',
            element:   '.note-popover button[data-event="color"]:visible',
            title:     "change text bg-color after triple click",
        },
        {
            waitFor:   '#editable_area > section .row > div:first:not(:has(p font)) h1 font',
            element:   '.note-color button.dropdown-toggle:visible',
            title:     "change selection to change text color",
            onload: function () {
                var $el = $('#editable_area > section .row > div:first:not(:has(p font)) h1 font');
                $.summernote.core.range.create($el[0].firstChild, 5, $el[0].firstChild, 10).select();
                click_event($el[0], 'mouseup');
            }
        },
        {
            element:   'div[data-target-event="foreColor"]:visible .note-color-row:eq(1) button[data-event="foreColor"]:first',
            title:     "change text color",
        },
        {
            waitFor:   '#editable_area > section .row > div:first h1 font:eq(2)',
            element:   '.note-color button.dropdown-toggle:visible',
            title:     "change selection to change text bg-color again",
            onload: function () {
                var $el = $('#editable_area > section .row > div:first h1 font:eq(2)');
                $.summernote.core.range.create($el.prev()[0].firstChild, 3, $el[0].firstChild, 10).select();
                click_event($el.prev()[0], 'mouseup');
            }
        },
        {
            element:   'div[data-target-event="backColor"] .colorpicker button[data-event="backColor"]:first',
            title:     "change text backColor again",
        },
        {
            waitFor:   '#editable_area > section .row > div:first h1 font:eq(4)',
            element:   '.note-color button.dropdown-toggle:visible',
            title:     "change selection (h1 and p) to change text color with class",
            onload: function () {
                var $el = $('#editable_area > section .row > div:first h1 font:eq(4)');
                $.summernote.core.range.create($el.prev()[0].firstChild, 3, $el.parent("h1").next("p")[0].firstChild, 30).select();
                click_event($el.prev()[0], 'mouseup');
            }
        },
        {
            element:   'div[data-target-event="foreColor"]:visible button[data-event="foreColor"][data-value^="text-"]:first',
            title:     "change text foreColor again",
        },
        {
            waitFor:   '#editable_area > section .row > div:first p font',
            element:   '.o_editable.note-editable.o_dirty',
            title:     "delete selection",
            keydown:   46 // delete
        },
        {
            waitFor:   '#editable_area > section .row > div:first:not(:has(p font)) h1',
            element:   '.o_editable.note-editable.o_dirty',
            title:     "clean and delete (backspace) an other selection",
            onload: function () {
                var $el = $(this.waitFor);
                $.summernote.core.range.createFromNode($el.next("p")[0]).clean();
                $.summernote.core.range.create($el.find('font:containsExact(ici)')[0].firstChild, 1, $el.next().next()[0].firstChild, 5).select();
                click_event($el.find('font:last')[0], 'mouseup');
            },
            keydown:   8 // backspace
        },
        {
            waitFor:   '#editable_area > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) ) h1',
            element:   '.o_editable.note-editable.o_dirty',
            title:     "delete an other selection",
            onload: function () {
                var $el = $(this.waitFor);
                $.summernote.core.range.create($el.find('font:first')[0].firstChild, 3, $el.next("p")[0].childNodes[2], 8).select();
                click_event($el.find('font:first')[0], 'mouseup');
            },
            keydown:   46
        },
        {
            waitFor:   '#editable_area > section .row > div:first:has( font:last:containsExact(Bat) )',
            element:   '.note-image-popover button[data-event="undo"]',
            title:     "undo",
        },
        {
            waitFor:   '#editable_area > section .row > div:first:has( font:last:containsExact(i) )',
            element:   '.note-air-popover button[data-event="undo"]',
            title:     "undo again",
        },
        {
            waitFor:   '#editable_area > section .row > div:first:not(:has(p font)) h1',
            element:   '.o_editable.note-editable.o_dirty',
            title:     "delete (backspace) after undo",
            keydown:   8 // backspace
        },
        {
            waitFor:   '#editable_area > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) )',
            element:   '#editable_area > section .row > div:first img[style*="25%"]',
            title:     "click on image",
        },
        {
            element:   '.note-image-popover:visible button[data-event="resize"][data-value="0.5"]',
            title:     "Click on resize half",
        },
        {
            waitFor:   '#editable_area > section .row > div:first img[style*="50%"]',
            element:   '.note-image-popover:visible button[data-event="showImageDialog"]',
            title:     "Click on edit picture",
        },
        {
            waitFor:   '.modal #editor-media-image',
            element:   '.modal a[data-toggle="tab"]:contains(Pictogram)',
            title:     "Click on pictogram tab",
        },
        {
            element:   '#editor-media-icon.active span.fa:first',
            title:     "select a pictogram",
        },
        {
            waitFor:   '#editor-media-icon.active span.font-icons-selected',
            element:   '.modal button.save',
            title:     "save pictogram",
        },
        {
            element:   '.note-image-popover button[data-event="resizefa"][data-value="3"]',
            title:     "select a size for the pictogram",
        },
        {
            waitFor:   '#wrapwrap span.fa-3x',
            element:   '.note-image-popover:visible button[data-event="floatMe"][data-value="right"]',
            title:     "click on float right",
        },
        {
            waitFor:   '#editable_area > section .row > div:first span.fa.pull-right',
            element:   '.note-image-popover:visible button[data-event="showLinkDialog"]',
            title:     "click on create link",
        },
        {
            waitFor:   '.modal a#link-preview:containsRegex(/^<span [^>]+><\\/span>$/) > span.fa.fa-3x.pull-right',
            element:   '.modal .dropdown:has(.link-style) a[data-toggle="dropdown"]',
            title:     "click on color style",
        },
        {
            element:   '.modal .dropdown ul label.btn-success',
            title:     "choose success style",
        },
        // {
        //     waitFor:   '.modal a#link-preview.btn:containsRegex(/^<span [^>]+><\\/span>$/)',
        //     element:   '.modal .select2-container.url-source a.select2-choice',
        //     title:     "click to choose an internal page",
        // },
        // {
        //     element:   '.select2-drop:visible .select2-search input',
        //     title:     "search 'contact'",
        //     sampleText: "contact",
        // },
        // {
        //     element:   '.select2-drop:visible .select2-results .select2-result div:contains(/page/)',
        //     title:     "select /page/contactus",
        // },
        {
        //    waitNot:   '.select2-drop:visible',
            element:   '#link-text',
            title:     "change text label",
            sampleText: "ABC[IMG] DEF",
        },
        {
            waitFor:   '.modal a#link-preview.btn',
            element:   '#link-external',
            sampleText: "http://www.odoo.com",
            title:     "insert a link url",
        },
        {
            waitFor:   '.modal a#link-preview.btn:containsRegex(/^ABC<span [^>]+><\\/span> DEF$/)',
            element:   '.modal button.save',
            title:     "save link",
        },
        {
            waitNot:   '#link-preview',
            waitFor:   'a.btn[href^="http://"]:has(span.fa.fa-3x.pull-right)',
            element:   '#editable_area > section .row > div:last img',
            title:     "click on other picture",
        },
        {
            waitFor:   '#editable_area > section .row > div:first span.fa.pull-right',
            element:   '.note-image-popover:visible button[data-event="showLinkDialog"]',
            title:     "click on create link again",
        },
        {
            waitFor:   '.modal a#link-preview:containsRegex(/^<img [^>]+>$/)',
            element:   '.modal .dropdown:has(.link-style) a[data-toggle="dropdown"]',
            title:     "click on color style again",
        },
        {
            element:   '.modal .dropdown ul label.btn-success',
            title:     "choose success style",
        },
        {
            waitFor:   '.modal a#link-preview.btn',
            element:   '#link-external',
            sampleText: "test@test.test",
            title:     "insert an email",
        },
        {
            waitFor:   '.modal a#link-preview.btn[href="mailto:test@test.test"]',
            element:   '.modal button.save',
            title:     "save link",
        },
        {
            waitNot:   '#link-preview',
            waitFor:   '#editable_area > section .row > div:eq(1) > a > img',
            element:   '#editable_area > section .row > div:first p:eq(2)',
            title:     "triple enter then double backspace",
            keydown:   [66, 13, 66, 13, 13, 8, 8], // B enter B enter enter backspace backspace
            onload: function () {
                var p = $(this.element)[0].firstChild;
                $.summernote.core.range.create(p, p.textContent.length, p, p.textContent.length).select();
                click_event(p, 'mouseup');
            },
        },
        {
            waitNot:   '#editable_area > section .row > div:first p:eq(4), #editable_area > section .row > div:eq(3)',
            waitFor:   '#editable_area > section .row > div:first p:eq(3)',
            title:     "add ul content",
            onload: function () {
                var $el = $('#editable_area > section .row > div:first');
                var html = '  <ul>     '+
                    '\n     <li>   <p>Batnae municipium.  </p></li>'+
                    '\n     <li>    Seleucia praeter.</li>'+
                    '\n     <li><p>Et hanc quidem.</p></li>'+
                    '\n    </ul>';
                $el.append(html);
                var node = $el.find('ul li p:last')[0].firstChild;
                $.summernote.core.range.create(node, 6).select();
                click_event(node, 'mouseup');
            }
        },
        {
            waitFor:   '#editable_area > section .row > div:first ul li p:first',
            element:   '.note-air-popover .note-style button.dropdown-toggle',
            title:     "click on style dropdown",
        },
        {
            element:   '.note-air-popover .note-style ul:visible a[data-value="h3"]',
            title:     "select h3",
            onload: function () {
                var node = $('#editable_area > section .row > div:first ul li p:last')[0].firstChild;
                $.summernote.core.range.create(node, 0).select();
                click_event(node, 'mouseup');
            }
        },
        {
            element:   '#editable_area > section .row > div:first > ul > li > h3',
            title:     "double tabulation",
            keydown:   [9, 9] // tabulation
        },
        {
            waitFor:   '#editable_area > section .row > div:first ul > li > ul > li > ul > li > h3',
            element:   '.note-air-popover button[data-event="insertOrderedList"]',
            title:     "click on order list",
        },
        {
            waitFor:   '#editable_area > section .row > div:first ul > li > ul > li > ol > li > h3',
            element:   '#editable_area > section .row > div:first ul li > p:last',
            title:     "enter in ul",
            keydown:   [66, 13], // enter
            onload: function () {
                $(this.element)[0].firstChild.textContent += "";
                $.summernote.core.range.create($(this.element)[0].firstChild, 7).select();
                click_event($(this.element)[0], 'mouseup');
            }
        },
        {
            element:   '#editable_area > section .row > div:first ul li > p:eq(1):containsRegex(/^municipium./)',
            title:     "backspace in list",
            keydown:   8
        },
        {
            waitFor:   '#editable_area > section .row > div:first ul li p:eq(1)',
            title:     "end",
        },
    ]
});


Tour.register({
    id:   'rte_inline',
    name: "Test RTE Inline",
    mode: 'test',
    path: '/web_editor/field/html/inline?callback=FieldTextHtml_0&enable_editor=1&datarecord=%7B%7D',
    steps: [
        {
            title:     "Change html for this test",
            onload: function () {
                var $el = $(this.element);
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
                $("#editable_area").html(html);
            }
        },
        {
            title:     "call clean for save",
            element:   '#wrapwrap table',
            onload: function () {
                snippet_editor.instance.clean_for_save();
            }
        },
        {
            waitFor:   '#wrapwrap img:first[width][height][style*="-radius"][style*="1px"][style*="padding"]',
            title:     "check the image style",
        },
        {
            waitFor:   '#wrapwrap img:eq(1)[src^="/web_editor/font_to_img/"][src$="/rgb(66,139,202)/32"]',
            title:     "check the font image src",
        },
        {
            waitFor:   '#wrapwrap img:eq(1)[height]:not([class*="fa"])',
            title:     "check the font class to css",
        },
        {
            waitFor:   '#wrapwrap img:eq(2)[style*="float:right"]',
            title:     "check the second font class to css",
        },
    ]
});


});

});
