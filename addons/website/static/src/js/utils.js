odoo.define('website.utils', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;

/**
 * Allows to load anchors from a page.
 *
 * @param {string} url
 * @returns {Deferred<string[]>}
 */
function loadAnchors(url) {
    return new Promise(function (resolve, reject) {
        if (url !== window.location.pathname && url[0] !== '#') {
            $.get(window.location.origin + url).then(resolve, reject);
        } else {
            resolve(document.body.outerHTML);
        }
    }).then(function (response) {
        return _.map($(response).find('[id][data-anchor=true]'), function (el) {
            return '#' + el.id;
        });
    });
}

/**
 * Allows the given input to propose existing website URLs.
 *
 * @param {ServicesMixin|Widget} self - an element capable to trigger an RPC
 * @param {jQuery} $input
 */
function autocompleteWithPages(self, $input, options) {
    $.widget("website.urlcomplete", $.ui.autocomplete, {
        options: options || {},
        _create: function () {
            this._super();
            this.widget().menu("option", "items", "> :not(.ui-autocomplete-category)");
        },
        _renderMenu: function (ul, items) {
            const self = this;
            items.forEach(item => {
                if (item.separator) {
                    self._renderSeparator(ul, item);
                }
                else {
                    self._renderItem(ul, item);
                }
            });
        },
        _renderSeparator: function (ul, item) {
            return $("<li class='ui-autocomplete-category font-weight-bold text-capitalize p-2'>")
                   .append(`<div>${item.separator}</div>`)
                   .appendTo(ul);
        },
        _renderItem: function (ul, item) {
            return $("<li>")
                   .data('ui-autocomplete-item', item)
                   .append(`<div>${item.label}</div>`)
                   .appendTo(ul);
        },
    });
    $input.urlcomplete({
        source: function (request, response) {
            if (request.term[0] === '#') {
                loadAnchors(request.term).then(function (anchors) {
                    response(anchors);
                });
            } else {
                return self._rpc({
                    route: '/website/get_suggested_links',
                    params: {
                        needle: request.term,
                        limit: 15,
                    }
                }).then(function (res) {
                    let choices = res.matching_pages;
                    res.others.forEach(other => {
                        if (other.values.length) {
                            choices = choices.concat(
                                [{separator: other.title}],
                                other.values,
                            );
                        }
                    });
                    response(choices);
                });
            }
        },
        select: function (ev, ui) {
            ev.target.value = ui.item.value;
            self.trigger_up('website_url_chosen');
            ev.preventDefault();
        },
    });
}

/**
 * @param {jQuery} $element
 * @param {jQuery} [$excluded]
 */
function onceAllImagesLoaded($element, $excluded) {
    var defs = _.map($element.find('img').addBack('img'), function (img) {
        if (img.complete || $excluded && ($excluded.is(img) || $excluded.has(img).length)) {
            return; // Already loaded
        }
        var def = new Promise(function (resolve, reject) {
            $(img).one('load', function () {
                resolve();
            });
        });
        return def;
    });
    return Promise.all(defs);
}

/**
 * @deprecated
 * @todo create Dialog.prompt instead of this
 */
function prompt(options, _qweb) {
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
     * @param {Function} [options.init] optional function that takes the `field` (enhanced with a fillWith() method) and the `dialog` as parameters [can return a promise]
     */
    if (typeof options === 'string') {
        options = {
            text: options
        };
    }
    var xmlDef;
    if (_.isUndefined(_qweb)) {
        _qweb = 'website.prompt';
        xmlDef = ajax.loadXML('/website/static/src/xml/website.xml', core.qweb);
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

    var def = new Promise(function (resolve, reject) {
        Promise.resolve(xmlDef).then(function () {
            var dialog = $(qweb.render(_qweb, options)).appendTo('body');
            options.$dialog = dialog;
            var field = dialog.find(options.field_type).first();
            field.val(options['default']); // dict notation for IE<9
            field.fillWith = function (data) {
                if (field.is('select')) {
                    var select = field[0];
                    data.forEach(function (item) {
                        select.options[select.options.length] = new window.Option(item[1], item[0]);
                    });
                } else {
                    field.val(data);
                }
            };
            var init = options.init(field, dialog);
            Promise.resolve(init).then(function (fill) {
                if (fill) {
                    field.fillWith(fill);
                }
                dialog.modal('show');
                field.focus();
                dialog.on('click', '.btn-primary', function () {
                    var backdrop = $('.modal-backdrop');
                    resolve({ val: field.val(), field: field, dialog: dialog });
                    dialog.modal('hide').remove();
                        backdrop.remove();
                });
            });
            dialog.on('hidden.bs.modal', function () {
                    var backdrop = $('.modal-backdrop');
                reject();
                dialog.remove();
                    backdrop.remove();
            });
            if (field.is('input[type="text"], select')) {
                field.keypress(function (e) {
                    if (e.which === 13) {
                        e.preventDefault();
                        dialog.find('.btn-primary').trigger('click');
                    }
                });
            }
        });
    });

    return def;
}

function websiteDomain(self) {
    var websiteID;
    self.trigger_up('context_get', {
        callback: function (ctx) {
            websiteID = ctx['website_id'];
        },
    });
    return ['|', ['website_id', '=', false], ['website_id', '=', websiteID]];
}

function sendRequest(route, params) {
    function _addInput(form, name, value) {
        let param = document.createElement('input');
        param.setAttribute('type', 'hidden');
        param.setAttribute('name', name);
        param.setAttribute('value', value);
        form.appendChild(param);
    }

    let form = document.createElement('form');
    form.setAttribute('action', route);
    form.setAttribute('method', params.method || 'POST');

    if (core.csrf_token) {
        _addInput(form, 'csrf_token', core.csrf_token);
    }

    for (const key in params) {
        const value = params[key];
        if (Array.isArray(value) && value.length) {
            for (const val of value) {
                _addInput(form, key, val);
            }
        } else {
            _addInput(form, key, value);
        }
    }

    document.body.appendChild(form);
    form.submit();
}

return {
    loadAnchors: loadAnchors,
    autocompleteWithPages: autocompleteWithPages,
    onceAllImagesLoaded: onceAllImagesLoaded,
    prompt: prompt,
    sendRequest: sendRequest,
    websiteDomain: websiteDomain,
};
});
