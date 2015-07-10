odoo.define('website.website', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var session = require('web.session');
var base = require('web_editor.base');
var Tour = require('web.Tour');

var qweb = core.qweb;
var _t = core._t;
base.url_translations = '/website/translations';

/* --- Set the browser into the dom for css selectors --- */
var browser;
if ($.browser.webkit) browser = "webkit";
else if ($.browser.safari) browser = "safari";
else if ($.browser.opera) browser = "opera";
else if ($.browser.msie || ($.browser.mozilla && +$.browser.version.replace(/^([0-9]+\.[0-9]+).*/, '\$1') < 20)) browser = "msie";
else if ($.browser.mozilla) browser = "mozilla";
browser += ","+$.browser.version;
if (/android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(navigator.userAgent.toLowerCase())) browser += ",mobile";
document.documentElement.setAttribute('data-browser', browser);

/* ----------------------------------------------------
   Helpers
   ---------------------------------------------------- */

var get_context = base.get_context;
base.get_context = base.get_context = function (dict) {
    var html = document.documentElement;
    return _.extend({
        'website_id': html.getAttribute('data-website-id')|0
    }, get_context(dict), dict);
};

/* ----------------------------------------------------
   Widgets
   ---------------------------------------------------- */ 

var prompt = function (options, _qweb) {
    /**
     * A bootstrapped version of prompt() albeit asynchronous
     * This was built to quickly prompt the user with a single field.
     * For anything more complex, please use editor.Dialog class
     *
     * Usage Ex:
     *
     * website.prompt("What... is your quest ?").then(function (answer) {
     *     arthur.reply(answer || "To seek the Holy Grail.");
     * });
     *
     * website.prompt({
     *     select: "Please choose your destiny",
     *     init: function() {
     *         return [ [0, "Sub-Zero"], [1, "Robo-Ky"] ];
     *     }
     * }).then(function (answer) {
     *     mame_station.loadCharacter(answer);
     * });
     *
     * @param {Object|String} options A set of options used to configure the prompt or the text field name if string
     * @param {String} [options.window_title=''] title of the prompt modal
     * @param {String} [options.input] tell the modal to use an input text field, the given value will be the field title
     * @param {String} [options.textarea] tell the modal to use a textarea field, the given value will be the field title
     * @param {String} [options.select] tell the modal to use a select box, the given value will be the field title
     * @param {Object} [options.default=''] default value of the field
     * @param {Function} [options.init] optional function that takes the `field` (enhanced with a fillWith() method) and the `dialog` as parameters [can return a deferred]
     */
    if (typeof options === 'string') {
        options = {
            text: options
        };
    }
    if (_.isUndefined(_qweb)) {
        _qweb = 'website.prompt';
    }
    options = _.extend({
        window_title: '',
        field_name: '',
        'default': '', // dict notation for IE<9
        init: function() {},
    }, options || {});

    var type = _.intersection(Object.keys(options), ['input', 'textarea', 'select']);
    type = type.length ? type[0] : 'input';
    options.field_type = type;
    options.field_name = options.field_name || options[type];

    var def = $.Deferred();
    var dialog = $(qweb.render(_qweb, options)).appendTo("body");
    options.$dialog = dialog;
    var field = dialog.find(options.field_type).first();
    field.val(options['default']); // dict notation for IE<9
    field.fillWith = function (data) {
        if (field.is('select')) {
            var select = field[0];
            data.forEach(function (item) {
                select.options[select.options.length] = new Option(item[1], item[0]);
            });
        } else {
            field.val(data);
        }
    };
    var init = options.init(field, dialog);
    $.when(init).then(function (fill) {
        if (fill) {
            field.fillWith(fill);
        }
        dialog.modal('show');
        field.focus();
        dialog.on('click', '.btn-primary', function () {
            def.resolve(field.val(), field, dialog);
            dialog.remove();
            $('.modal-backdrop').remove();
        });
    });
    dialog.on('hidden.bs.modal', function () {
        def.reject();
        dialog.remove();
        $('.modal-backdrop').remove();
    });
    if (field.is('input[type="text"], select')) {
        field.keypress(function (e) {
            if (e.which == 13) {
                e.preventDefault();
                dialog.find('.btn-primary').trigger('click');
            }
        });
    }
    return def;
};

var error = function(data, url) {
    var $error = $(qweb.render('website.error_dialog', {
        'title': data.data ? data.data.arguments[0] : "",
        'message': data.data ? data.data.arguments[1] : data.statusText,
        'backend_url': url
    }));
    $error.appendTo("body");
    $error.modal('show');
};

var form = function (url, method, params) {
    var form = document.createElement('form');
    form.setAttribute('action', url);
    form.setAttribute('method', method);
    _.each(params, function (v, k) {
        var param = document.createElement('input');
        param.setAttribute('type', 'hidden');
        param.setAttribute('name', k);
        param.setAttribute('value', v);
        form.appendChild(param);
    });
    document.body.appendChild(form);
    form.submit();
};

var init_kanban = function ($kanban) {
    $('.js_kanban_col', $kanban).each(function () {
        var $col = $(this);
        var $pagination = $('.pagination', $col);
        if(!$pagination.size()) {
            return;
        }

        var page_count =  $col.data('page_count');
        var scope = $pagination.last().find("li").size()-2;
        var kanban_url_col = $pagination.find("li a:first").attr("href").replace(/[0-9]+$/, '');

        var data = {
            'domain': $col.data('domain'),
            'model': $col.data('model'),
            'template': $col.data('template'),
            'step': $col.data('step'),
            'orderby': $col.data('orderby')
        };

        $pagination.on('click', 'a', function (ev) {
            ev.preventDefault();
            var $a = $(ev.target);
            if($a.parent().hasClass('active')) {
                return;
            }

            var page = +$a.attr("href").split(",").pop().split('-')[1];
            data['page'] = page;

            $.post('/website/kanban', data, function (col) {
                $col.find("> .thumbnail").remove();
                $pagination.last().before(col);
            });

            var page_start = page - parseInt(Math.floor((scope-1)/2), 10);
            if (page_start < 1 ) page_start = 1;
            var page_end = page_start + (scope-1);
            if (page_end > page_count ) page_end = page_count;

            if (page_end - page_start < scope) {
                page_start = page_end - scope > 0 ? page_end - scope : 1;
            }

            $pagination.find('li.prev a').attr("href", kanban_url_col+(page-1 > 0 ? page-1 : 1));
            $pagination.find('li.next a').attr("href", kanban_url_col+(page < page_end ? page+1 : page_end));
            for(var i=0; i < scope; i++) {
                $pagination.find('li:not(.prev):not(.next):eq('+i+') a').attr("href", kanban_url_col+(page_start+i)).html(page_start+i);
            }
            $pagination.find('li.active').removeClass('active');
            $pagination.find('li:has(a[href="'+kanban_url_col+page+'"])').addClass('active');

        });

    });
};

ajax.loadXML('/website/static/src/xml/website.xml', qweb);

/**
 * Execute a function if the dom contains at least one element matched
 * through the given jQuery selector. Will first wait for the dom to be ready.
 *
 * @param {String} selector A jQuery selector used to match the element(s)
 * @param {Function} fn Callback to execute if at least one element has been matched
 */
var if_dom_contains = function(selector, fn) {
    base.dom_ready.then(function () {
        var elems = $(selector);
        if (elems.length) {
            fn(elems);
        }
    });
};

/**
 * Cancel the auto run of Tour (test) and launch the tour after tob bar all bind events
 */
 
Tour.autoRunning = false;
base.ready().then(function () {
    data.topBar = new TopBar();
    data.topBar.attachTo($("#oe_main_menu_navbar"))
        .then(function () {
            setTimeout(Tour.running,0);
        });
});

/**
 * Returns a deferred resolved when the templates are loaded
 * and the Widgets can be instanciated.
 */
 
base.dom_ready.then(function () {
    /* ----- PUBLISHING STUFF ---- */
    $(document).on('click', '.js_publish_management .js_publish_btn', function () {
        var $data = $(this).parents(".js_publish_management:first");
        var self=this;
        ajax.jsonRpc($data.data('controller') || '/website/publish', 'call', {'id': +$data.data('id'), 'object': $data.data('object')})
            .then(function (result) {
                $data.toggleClass("css_unpublished css_published");
                $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
            }).fail(function (err, data) {
                error(data, '/web#return_label=Website&model='+$data.data('object')+'&id='+$data.data('id'));
            });
        });

        if (!$('.js_change_lang').length) {
            // in case template is not up to date...
            var links = $('ul.js_language_selector li a:not([data-oe-id])');
            var m = $(_.min(links, function(l) { return $(l).attr('href').length; })).attr('href');
            links.each(function() {
                var t = $(this).attr('href');
                var l = (t === m) ? "default" : t.split('/')[1];
                $(this).data('lang', l).addClass('js_change_lang');
            });
        }

        $(document).on('click', '.js_change_lang', function(e) {
            e.preventDefault();

            var self = $(this);
            // retrieve the hash before the redirect
            var redirect = {
                lang: self.data('lang'),
                url: encodeURIComponent(self.attr('href').replace(/[&?]edit_translations[^&?]+/, '')),
                hash: location.hash
            };
            location.href = _.str.sprintf("/website/lang/%(lang)s?r=%(url)s%(hash)s", redirect);
    });

    /* ----- KANBAN WEBSITE ---- */
    $('.js_kanban').each(function () {
        init_kanban(this);
    });

    $('.js_website_submit_form').on('submit', function() {
        var $buttons = $(this).find('button[type="submit"], a.a-submit');
        _.each($buttons, function(btn) {
            $(btn).attr('data-loading-text', '<i class="fa fa-spinner fa-spin"></i> ' + $(btn).text()).button('loading');
        });
    });

    setTimeout(function () {
        if (window.location.hash.indexOf("scrollTop=") > -1) {
            window.document.body.scrollTop = +location.hash.match(/scrollTop=([0-9]+)/)[1];
        }
    },0);
});


/**
 * Object who contains all method and bind for the top bar, the template is create server side.
 */

var TopBar = Widget.extend({
    start: function () {
        var $collapse = this.$('#oe_applications ul.dropdown-menu').clone()
                .attr("id", "oe_applications_collapse")
                .attr("class", "nav navbar-nav navbar-left navbar-collapse collapse");
        this.$('#oe_applications').before($collapse);
        $collapse.wrap('<div class="visible-xs"/>');
        this.$('[data-target="#oe_applications"]').attr("data-target", "#oe_applications_collapse");

        return this._super();
    }
});


var data = {
    prompt: prompt,
    form: form,
    if_dom_contains: if_dom_contains,
    TopBar: TopBar,
    ready: function () {
        console.warn("website.ready is deprecated: Please use require('web_editor.base').ready()");
        return base.ready();
    }
};
return data;

});

$(function () {
    odoo.init();
});
