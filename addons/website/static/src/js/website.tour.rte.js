(function () {
    'use strict';

    var _t = openerp._t;

    var click_event = function(el, type) {
        var evt = document.createEvent("MouseEvents");
        evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
        el.dispatchEvent(evt);
    };

    openerp.Tour.register({
        id:   'website_rte',
        name: "Test website RTE",
        path: '/page/homepage',
        mode: 'test',
        steps: [
            {
                element:   'button[data-action=edit]',
                title:     "Edit this page",
                wait:      250
            },
            {
                snippet:   '#snippet_structure .oe_snippet:has(.s_text_image)',
                title:     "Drag & Drop a Text-Image Block",
            },
            {
                element:   '.oe_overlay_options:visible .oe_options a:first',
                title:     "Customize",
                onload: function () {
                    $(".oe_overlay_options:visible .snippet-option-background > ul").show();
                }
            },
            {
                element:   '.oe_overlay_options:visible .snippet-option-background > ul li[data-background*="quote"]:first a',
                title:     "Chose a background image",
            },
            {
                title:     "Change html for this test",
                waitFor:   '#wrapwrap > main > div > section:first[style*="background-image"]',
                element:   '#wrapwrap > main > div > section .row > div:first',
                onload: function () {
                    var $el = $(this.element);
                    var html = '<h1 id="text_title_id">Batnae municipium in Anthemusia</h1>     '+
                        '\n     <p>Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab Euphrate flumine brevi spatio disparatur, refertum mercatoribus opulentis, ubi annua sollemnitate prope Septembris initium mensis ad.</p>'+
                        '\n     <p>    Quam <img style="width: 25%" src="/website/static/src/img/text_image.png"/> quidem <span class="fa fa-flag fa-2x"></span> partem accusationis admiratus sum et moleste tuli potissimum esse Atratino datam. Neque enim decebat neque aetas.</p>'+
                        '\n     <p>Et hanc quidem praeter oppida multa duae civitates exornant Seleucia opus Seleuci regis, et Claudiopolis quam deduxit coloniam Claudius Caesar. Isaura enim antehac nimium potens, olim subversa ut rebellatrix.</p>'+
                        '<p>Harum trium sententiarum nulli prorsus assentior.</p>';
                    $el.html(html);
                }
            },
            {
                element:   '#wrapwrap > main > div > section .row > div:first',
                title:     "simulate triple click and change text bg-color",
                onload: function () {
                    var $el = $(this.element);
                    var $h1 = $('h1', $el);
                    $.summernote.core.range.create($h1[0].firstChild, 0, $('p', $el)[0], 0).select();
                    click_event($h1[0], 'mouseup');
                }
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first',
                element:   '.note-popover button[data-event="color"]:visible',
                title:     "change text bg-color after triple click",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first:not(:has(p font)) h1 font',
                element:   '.note-color button.dropdown-toggle:visible',
                title:     "change selection to change text color",
                onload: function () {
                    var $el = $('#wrapwrap > main > div > section .row > div:first:not(:has(p font)) h1 font');
                    $.summernote.core.range.create($el[0].firstChild, 5, $el[0].firstChild, 10).select();
                    click_event($el[0], 'mouseup');
                }
            },
            {
                element:   'div[data-target-event="foreColor"]:visible .note-color-row:eq(1) button[data-event="foreColor"]:first',
                title:     "change text color",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first h1 font:eq(2)',
                element:   '.note-color button.dropdown-toggle:visible',
                title:     "change selection to change text bg-color again",
                onload: function () {
                    var $el = $('#wrapwrap > main > div > section .row > div:first h1 font:eq(2)');
                    $.summernote.core.range.create($el.prev()[0].firstChild, 3, $el[0].firstChild, 10).select();
                    click_event($el.prev()[0], 'mouseup');
                }
            },
            {
                element:   'div[data-target-event="backColor"]:visible .colorpicker button[data-event="backColor"]:first',
                title:     "change text backColor again",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first h1 font:eq(4)',
                element:   '.note-color button.dropdown-toggle:visible',
                title:     "change selection (h1 and p) to change text color with class",
                onload: function () {
                    var $el = $('#wrapwrap > main > div > section .row > div:first h1 font:eq(4)');
                    $.summernote.core.range.create($el.prev()[0].firstChild, 3, $el.parent("h1").next("p")[0].firstChild, 30).select();
                    click_event($el.prev()[0], 'mouseup');
                }
            },
            {
                element:   'div[data-target-event="foreColor"]:visible button[data-event="foreColor"][data-value^="text-"]:first',
                title:     "change text foreColor again",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first p font',
                element:   '.o_editable.note-editable.o_dirty',
                title:     "delete selection",
                keydown:   46 // delete
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first:not(:has(p font)) h1',
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
                waitFor:   '#wrapwrap > main > div > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) ) h1',
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
                waitFor:   '#wrapwrap > main > div > section .row > div:first:has( font:last:containsExact(Bat) )',
                element:   '.note-image-popover button[data-event="undo"]',
                title:     "undo",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first:has( font:last:containsExact(i) )',
                element:   '.note-air-popover button[data-event="undo"]',
                title:     "undo adain",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first:not(:has(p font)) h1',
                element:   '.o_editable.note-editable.o_dirty',
                title:     "delete (backspace) after undo",
                keydown:   8 // backspace
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first:has( font:last:containsExact(i) ):has( p:first:containsRegex(/^uam/) )',
                element:   '#wrapwrap > main > div > section .row > div:first img[style*="25%"]',
                title:     "click on image",
            },
            {
                element:   '.note-image-popover:visible button[data-event="resize"][data-value="0.5"]',
                title:     "Click on resize half",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first img[style*="50%"]',
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
                waitFor:   '#wrapwrap > main > div > section .row > div:first span.fa.pull-right',
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
            {
                waitFor:   '.modal a#link-preview.btn:containsRegex(/^<span [^>]+><\\/span>$/)',
                element:   '.modal .select2-container.url-source a.select2-choice',
                title:     "click to choose an internal page",
            },
            {
                element:   '.select2-drop:visible .select2-search input',
                title:     "search 'contact'",
                sampleText: "contact",
            },
            {
                element:   '.select2-drop:visible .select2-results .select2-result div:contains(/page/)',
                title:     "select /page/contactus",
            },
            {
                waitNot:   '.select2-drop:visible',
                element:   '#link-text',
                title:     "change text label",
                sampleText: "ABC[IMG] DEF",
            },
            {
                waitFor:   '.modal a#link-preview.btn:containsRegex(/^ABC<span [^>]+><\\/span> DEF$/)',
                element:   '.modal button.save',
                title:     "save link",
            },
            {
                waitNot:   '#link-preview',
                waitFor:   'a.btn[href^="/"]:has(span.fa.fa-3x.pull-right)',
                element:   '#wrapwrap > main > div > section .row > div:last img',
                title:     "click on other picture",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first span.fa.pull-right',
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
                waitFor:   '#wrapwrap > main > div > section .row > div:eq(1) > a > img',
                element:   '#wrapwrap > main > div > section .row > div:first p:eq(2)',
                title:     "triple enter then double backspace",
                keydown:   [66, 13, 66, 13, 13, 8, 8], // B enter B enter enter backspace backspace
                onload: function () {
                    var p = $(this.element)[0].firstChild;
                    $.summernote.core.range.create(p, p.textContent.length, p, p.textContent.length).select();
                    click_event(p, 'mouseup');
                },
            },
            {
                waitNot:   '#wrapwrap > main > div > section .row > div:first p:eq(4), #wrapwrap > main > div > section .row > div:eq(3)',
                waitFor:   '#wrapwrap > main > div > section .row > div:first p:eq(3)',
                title:     "add ul content",
                onload: function () {
                    var $el = $('#wrapwrap > main > div > section .row > div:first');
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
                waitFor:   '#wrapwrap > main > div > section .row > div:first ul li p:first',
                element:   '.note-air-popover .note-style button.dropdown-toggle',
                title:     "click on style dropdown",
            },
            {
                element:   '.note-air-popover .note-style ul:visible a[data-value="h3"]',
                title:     "select h3",
                onload: function () {
                    var node = $('#wrapwrap > main > div > section .row > div:first ul li p:last')[0].firstChild;
                    $.summernote.core.range.create(node, 0).select();
                    click_event(node, 'mouseup');
                }
            },
            {
                element:   '#wrapwrap > main > div > section .row > div:first > ul > li > h3',
                title:     "double tabulation",
                keydown:   [9, 9] // tabulation
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first ul > li > ul > li > ul > li > h3',
                element:   '.note-air-popover button[data-event="insertOrderedList"]',
                title:     "click on order list",
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first ul > li > ul > li > ol > li > h3',
                element:   '#wrapwrap > main > div > section .row > div:first ul li > p:last',
                title:     "enter in ul",
                keydown:   [66, 13], // enter
                onload: function () {
                    $(this.element)[0].firstChild.textContent += "";
                    $.summernote.core.range.create($(this.element)[0].firstChild, 7).select();
                    click_event($(this.element)[0], 'mouseup');
                }
            },
            {
                element:   '#wrapwrap > main > div > section .row > div:first ul li > p:eq(1):containsRegex(/^municipium./)',
                title:     "backspace in list",
                keydown:   8
            },
            {
                waitFor:   '#wrapwrap > main > div > section .row > div:first ul li p:eq(1)',
                title:     "end",
            },
        ]
    });

}());
