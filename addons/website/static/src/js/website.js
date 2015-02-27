(function() {
    "use strict";

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
    /* ---------------------------------------------------- */

    var website = {};
    openerp.website = website;

    website.translatable = !!$('html').data('translatable');

    /* ----------------------------------------------------
       Helpers
       ---------------------------------------------------- */ 
    website.get_context = function (dict) {
        var html = document.documentElement;
        return _.extend({
            lang: html.getAttribute('lang').replace('-', '_'),
            website_id: html.getAttribute('data-website-id')|0
        }, dict);
    };

    website.parseQS = function (qs) {
        var match,
            params = {},
            pl     = /\+/g,  // Regex for replacing addition symbol with a space
            search = /([^&=]+)=?([^&]*)/g;

        while ((match = search.exec(qs))) {
            var name = decodeURIComponent(match[1].replace(pl, " "));
            var value = decodeURIComponent(match[2].replace(pl, " "));
            params[name] = value;
        }
        return params;
    };

    var parsedSearch;
    website.parseSearch = function () {
        if (!parsedSearch) {
            parsedSearch = website.parseQS(window.location.search.substring(1));
        }
        return parsedSearch;
    };

    website.parseHash = function () {
        return website.parseQS(window.location.hash.substring(1));
    };

    website.reload = function () {
        location.hash = "scrollTop=" + window.document.body.scrollTop;
        if (location.search.indexOf("enable_editor") > -1) {
            window.location.href = window.location.href.replace(/enable_editor(=[^&]*)?/g, '');
        } else {
            window.location.reload();
        }
    };

    /* ----------------------------------------------------
       Widgets
       ---------------------------------------------------- */ 

    website.prompt = function (options) {
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
        options = _.extend({
            window_title: '',
            field_name: '',
            'default': '', // dict notation for IE<9
            init: function() {}
        }, options || {});

        var type = _.intersection(Object.keys(options), ['input', 'textarea', 'select']);
        type = type.length ? type[0] : 'text';
        options.field_type = type;
        options.field_name = options.field_name || options[type];

        var def = $.Deferred();
        var dialog = $(openerp.qweb.render('website.prompt', options)).appendTo("body");
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

    website.error = function(data, url) {
        var $error = $(openerp.qweb.render('website.error_dialog', {
            'title': data.data ? data.data.arguments[0] : "",
            'message': data.data ? data.data.arguments[1] : data.statusText,
            'backend_url': url
        }));
        $error.appendTo("body");
        $error.modal('show');
    };

    website.form = function (url, method, params) {
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

    website.init_kanban = function ($kanban) {
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

    /* ----------------------------------------------------
       Async Ready and Template loading
       ---------------------------------------------------- */ 
    var templates_def = $.Deferred().resolve();
    website.add_template_file = function(template) {
        templates_def = templates_def.then(function() {
            var def = $.Deferred();
            openerp.qweb.add_template(template, function(err) {
                if (err) {
                    def.reject(err);
                } else {
                    def.resolve();
                }
            });
            return def;
        });
    };

    website.add_template_file('/website/static/src/xml/website.xml');

    website.dom_ready = $.Deferred();
    $(document).ready(function () {
        website.dom_ready.resolve();
        // fix for ie
        if($.fn.placeholder) $('input, textarea').placeholder();
    });

    /**
     * Execute a function if the dom contains at least one element matched
     * through the given jQuery selector. Will first wait for the dom to be ready.
     *
     * @param {String} selector A jQuery selector used to match the element(s)
     * @param {Function} fn Callback to execute if at least one element has been matched
     */
    website.if_dom_contains = function(selector, fn) {
        website.dom_ready.then(function () {
            var elems = $(selector);
            if (elems.length) {
                fn(elems);
            }
        });
    };

    var all_ready = null;
    /**
     * Returns a deferred resolved when the templates are loaded
     * and the Widgets can be instanciated.
     */
    website.ready = function() {
        if (!all_ready) {
            all_ready = website.dom_ready.then(function () {
                return templates_def;
            }).then(function () {
                // display button if they are at least one editable zone in the page (check the branding)
                if (!!$('[data-oe-model]').size()) {
                    $("#oe_editzone").show();

                    //backwards compatibility with 8.0RC1 templates - Drop next line in master!
                    $("#oe_editzone button").show();
                }

                if ($('html').data('website-id')) {
                    website.id = $('html').data('website-id');
                    website.session = new openerp.Session();
                    var modules = ['website'];
                    return openerp._t.database.load_translations(website.session, modules, website.get_context().lang);
                }
            }).promise();
        }
        return all_ready;
    };

    website.inject_tour = function() {
        // if a tour is active inject tour js
    };

    website.dom_ready.then(function () {
        /* ----- PUBLISHING STUFF ---- */
        $(document).on('click', '.js_publish_management .js_publish_btn', function () {
            var $data = $(this).parents(".js_publish_management:first");
            var self=this;
            openerp.jsonRpc($data.data('controller') || '/website/publish', 'call', {'id': +$data.data('id'), 'object': $data.data('object')})
                .then(function (result) {
                    $data.toggleClass("css_unpublished css_published");
                    $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
                }).fail(function (err, data) {
                    website.error(data, '/web#return_label=Website&model='+$data.data('object')+'&id='+$data.data('id'));
                });
        });

        /* ----- KANBAN WEBSITE ---- */
        $('.js_kanban').each(function () {
            website.init_kanban(this);
        });

        setTimeout(function () {
            if (window.location.hash.indexOf("scrollTop=") > -1) {
                window.document.body.scrollTop = +location.hash.match(/scrollTop=([0-9]+)/)[1];
            }
        },0);

        /* ----- WEBSITE TOP BAR ---- */
        var $collapse = $('#oe_applications ul.dropdown-menu').clone()
                .attr("id", "oe_applications_collapse")
                .attr("class", "nav navbar-nav navbar-left navbar-collapse collapse");
        $('#oe_applications').before($collapse);
        $collapse.wrap('<div class="visible-xs"/>');
        $('[data-target="#oe_applications"]').attr("data-target", "#oe_applications_collapse");
    });

    return website;
})();
