odoo.define('website.website', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var Dialog = require("web.Dialog");
    var core = require('web.core');
    var Widget = require('web.Widget');
    var session = require('web.session');
    var base = require('web_editor.base');
    var utils = require('web.utils');

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
         *     init: function () {
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
            init: function () {},
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
                    var backdrop = $('.modal-backdrop');
                def.resolve(field.val(), field, dialog);
                dialog.modal('hide').remove();
                    backdrop.remove();
            });
        });
        dialog.on('hidden.bs.modal', function () {
                var backdrop = $('.modal-backdrop');
            def.reject();
            dialog.remove();
                backdrop.remove();
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

    var error = function (title, message, url) {
        return new Dialog(null, {
            title: title || "",
            $content: $(qweb.render('website.error_dialog', {
                message: message || "",
                backend_url: url,
            })),
        }).open();
    };

    function _add_input(form, name, value) {
        var param = document.createElement('input');
        param.setAttribute('type', 'hidden');
        param.setAttribute('name', name);
        param.setAttribute('value', value);
        form.appendChild(param);
    }
    var form = function (url, method, params) {
        var form = document.createElement('form');
        form.setAttribute('action', url);
        form.setAttribute('method', method);

        if (core.csrf_token) {
            _add_input(form, 'csrf_token', core.csrf_token);
        }
        _.each(params, function (v, k) {
            _add_input(form, k, v);
        });
        document.body.appendChild(form);
        form.submit();
    };

    ajax.loadXML('/web/static/src/xml/base_common.xml', qweb).then(function () {
        ajax.loadXML('/website/static/src/xml/website.xml', qweb);
    });

    base.ready().then(function () {
        data.topBar = new TopBar();
        return data.topBar.attachTo($("#oe_main_menu_navbar"));
    });

    /* ----- PUBLISHING STUFF ---- */
    $(document).on('click', '.js_publish_management .js_publish_btn', function (e) {
        e.preventDefault();

        var $data = $(this).parents(".js_publish_management:first");
        ajax.jsonRpc($data.data('controller') || '/website/publish', 'call', {'id': +$data.data('id'), 'object': $data.data('object')})
            .then(function (result) {
                $data.toggleClass("css_unpublished css_published");
                $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
            }).fail(function (err, data) {
                error(data.data ? data.data.arguments[0] : "", data.data ? data.data.arguments[1] : data.statusText, '/web#return_label=Website&model='+$data.data('object')+'&id='+$data.data('id'));
            });
        });

        if (!$('.js_change_lang').length) {
            // in case template is not up to date...
            var links = $('ul.js_language_selector li a:not([data-oe-id])');
            var m = $(_.min(links, function (l) { return $(l).attr('href').length; })).attr('href');
            links.each(function () {
                var t = $(this).attr('href');
                var l = (t === m) ? "default" : t.split('/')[1];
                $(this).data('lang', l).addClass('js_change_lang');
            });
        }

        $(document).on('click', '.js_change_lang', function (e) {
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

    $('body').on('submit', '.js_website_submit_form', function() {
        var $buttons = $(this).find('button[type="submit"], a.a-submit');
        _.each($buttons, function (btn) {
            $(btn).attr('data-loading-text', '<i class="fa fa-spinner fa-spin"></i> ' + $(btn).text()).button('loading');
        });
    });

    _.defer(function () {
        if (window.location.hash.indexOf("scrollTop=") > -1) {
            window.document.body.scrollTop = +location.hash.match(/scrollTop=([0-9]+)/)[1];
        }
    });

    // display image thumbnail
    $(".o_image[data-mimetype^='image']").each(function () {
        var $img = $(this);
        if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
            $img.css('background-image', "url('" + $img.data('src') + "')");
        }
    });

    /* Load localizations */
    var lang = utils.get_cookie('website_lang') || $('html').attr('lang') || 'en_US';
    var localeDef = ajax.loadJS('/web/webclient/locale/' + lang.replace('-', '_'));

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

            var self = this;
            this.$el.on('mouseover', '> ul > li.dropdown:not(.open)', function (e) {
                var $opened = self.$('> ul > li.dropdown.open');
                if($opened.length) {
                    $opened.removeClass('open');
                    $(e.currentTarget).find('.dropdown-toggle').mousedown().focus().mouseup().click();
                }
            });

            this.$el.on('click', '.o_mobile_menu_toggle', function (ev) {
                self.$el.parent().toggleClass('o_mobile_menu_opened');
            });

            return this._super.apply(this, arguments);
        }
    });

    // enable magnify on zommable img
    $('.zoomable img[data-zoom]').zoomOdoo();

    Dialog.include({
        init: function () {
            this._super.apply(this, arguments);
            this.$modal.addClass("o_website_modal");
        },
    });

    var data = {
        prompt: prompt,
        error: error,
        form: form,
        TopBar: TopBar,
        ready: function () {
            console.warn("website.ready is deprecated: Please use require('web_editor.base').ready()");
            return base.ready();
        },
        localeDef: localeDef,
    };
    return data;
});
