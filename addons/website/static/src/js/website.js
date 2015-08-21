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
            dialog.modal('hide').remove();
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


ajax.loadXML('/website/static/src/xml/website.xml', qweb);
ajax.loadXML('/web/static/src/xml/base_common.xml', qweb);

/**
 * Cancel the auto run of Tour (test) and launch the tour after tob bar all bind events
 */
 
base.ready().then(function () {
    data.topBar = new TopBar();
    data.topBar.attachTo($("#oe_main_menu_navbar"));
});

/**
 * Returns a deferred resolved when the templates are loaded
 * and the Widgets can be instanciated.
 */

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
                hash: encodeURIComponent(location.hash)
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
    TopBar: TopBar,
    ready: function () {
        console.warn("website.ready is deprecated: Please use require('web_editor.base').ready()");
        return base.ready();
    }
};
return data;

});


odoo.define('website.search_box', function (require) {
"use strict";

var ajax = require('web.ajax');
var base = require('web_editor.base');
var core = require('web.core');
var _t = core._t;

$( "form.o_search_bar").each(function () {
    var $form = $(this);

    var $select = $form.find('input.o_search_select');
    $select.val('').select2({
            placeholder: _t("Search..."),
            maximumSelectionSize: 4,
            //minimumInputLength: 1,
            multiple: true,
            allowClear: false,
            closeOnSelect: false,
            openOnEnter: false,
            ajax: {
                cache: true,
                url: function (term) {
                    var datas = $select.select2('data');
                    return '/website/search_bar?' + $.param({
                            module: $form.data('module') || _.find(_.pluck(datas, 'module')),
                            needle: encodeURIComponent(_.str.strip(term)),
                        });
                },
                results: function (results, s, req) {
                    var datas = $select.select2('data');
                    var module = $form.data('module') || _.find(_.pluck(datas, 'module'));

                    if (module) {
                        results = _.filter(results, function (r) {
                            return !r.module || r.module == module;
                        });
                    }

                    function add_parent_data(parent, children) {
                        return _.filter(children, function (c) {
                            if (parent) {
                                c.title = parent.text;
                                c.module = parent.module;
                                c.error = parent.error;
                                c.url = parent.url;
                            }

                            if (datas.length && c.title && _.find(datas, function (d) { return c.title == d.title; })) {
                                return false;
                            }
                            if (c.children) {
                                c.children = add_parent_data(c, c.children);
                                return !!c.children.length;
                            } else {
                                return true;
                            }
                        });
                    }
                    results = add_parent_data(null, results);

                    results.sort(function (a, b) { return a.title != b.title ? (b.title > a.title ? -1 : 1) : (b.text > a.text ? -1 : 1); });

                    if (_.str.strip(req.term)) {
                        results.unshift({
                            id: '?search=' + encodeURIComponent(req.term),
                            text: req.term
                        });
                    }

                    return {
                        results: results
                    };
                },
            },
            formatResultCssClass: function (select){
                return select.error ? 'bg-danger' : '';
            },
            formatSelectionCssClass: function (select, $div) {
                if ($div.text().length > 24) {
                    $div.attr('title', $div.text());
                    $div.text($div.text().slice(0, 22) + '...');
                }
                return select.id.indexOf('?search=') === 0 ? 'o_search_search' : 'o_search_category';
            },
        });

    $select.data('select2').container.on('keypress', 'input', function (event) {
         if (event.keyCode === 13) {
             $form.submit();
         }
     });

    // default or previous search
    var searches = localStorage.getItem('o_search_bar') || '{}';
    if (searches) {
        searches = JSON.parse(searches);
        _.each(searches, function (datas, url) {
            if (window.location.href.indexOf(url) === -1) {
                return;
            }

            datas = _.filter(datas, function (d) {
                if (d.id[0] !== '?') {
                    // check id in location.href or convert slug into location.search
                    return window.location.href.indexOf(d.id) !==-1 ||
                    (d.id.indexOf('/') === 0 && window.location.search.indexOf(d.id.split('/')[1] + '=' + _.last(d.id.split('-'))) !==-1);
                }
                if (d.id.indexOf('?search=') === 0) {
                    var s = window.location.search.match(/search=([^=&]*)/);
                    return s && s[1].split(',').indexOf(d.id.slice(8)) !== -1;
                }
                return window.location.search.indexOf(d.id) !==-1 || window.location.search.indexOf('&' + d.id.slice(1)) !==-1;
            });
            $select.select2("data", datas);
        });
    }


    // compute data and redirect
    $form.on('submit', function (event) {
        event.preventDefault();
        var datas = $select.select2('data');
        datas.sort(function (a, b) {
            return a.id.indexOf('?search=') === b.id.indexOf('?search=') ?
                (a.title != b.title ? (b.title > a.title ? -1 : 1) : (b.text > a.text ? -1 : 1)) :
                (a.id.indexOf('?search=') ? -1 : 1);
        });

        searches[_.find(_.pluck(datas, 'url')) || '/'] = datas;
        localStorage.setItem('o_search_bar', JSON.stringify(searches));

        if (datas.length) {
            var get = [];
            var search = '';
            var url = (_.find(datas, function (data) { return data.url; }) || {}).url || window.location.href.replace(/\?.*/, '');

            _.each(datas, function (data) {
                if (data.id.indexOf('?search=') === 0) {
                    search += (search ? ',' : '') + _.str.strip(data.id.slice(8));
                } else if (data.id.indexOf('?') === 0) {
                    get.push(data.id.slice(1));
                } else {
                    url += data.id;
                }
            });

            if (search) {
                get.push('search=' + search);
            }
            if (odoo.debug) {
                get.push('debug');
            }

            window.location.href = url + '?' + get.join('&');
        }
        return false;
    });
});

});
