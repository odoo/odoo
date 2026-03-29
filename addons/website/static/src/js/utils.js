odoo.define('website.utils', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');

const { qweb, _t } = core;

/**
 * Allows to load anchors from a page.
 *
 * @param {string} url
 * @returns {Deferred<string[]>}
 */
function loadAnchors(url) {
    return new Promise(function (resolve, reject) {
        if (url === window.location.pathname || url[0] === '#') {
            resolve(document.body.outerHTML);
        } else if (url.length && !url.startsWith("http")) {
            $.get(window.location.origin + url).then(resolve, reject);
        } else { // avoid useless query
            resolve();
        }
    }).then(function (response) {
        const anchors = _.map($(response).find('[id][data-anchor=true]'), function (el) {
            return '#' + el.id;
        });
        // Always suggest the top and the bottom of the page as internal link
        // anchor even if the header and the footer are not in the DOM. Indeed,
        // the "scrollTo" function handles the scroll towards those elements
        // even when they are not in the DOM.
        if (!anchors.includes('#top')) {
            anchors.unshift('#top');
        }
        if (!anchors.includes('#bottom')) {
            anchors.push('#bottom');
        }
        return anchors;
    }).catch(error => {
        console.debug(error);
        return [];
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
            } else if (request.term.startsWith('http') || request.term.length === 0) {
                // avoid useless call to /website/get_suggested_links
                response();
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
            // choose url in dropdown with arrow change ev.target.value without trigger_up
            // so cannot check here if value has been updated
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
        btn_primary_title: _t('Create'),
        btn_secondary_title: _t('Cancel'),
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

/**
 * Converts a base64 SVG into a base64 PNG.
 *
 * @param {string|HTMLImageElement} src - an URL to a SVG or a *loaded* image
 *      with such an URL. This allows the call to potentially be a bit more
 *      efficient in that second case.
 * @returns {Promise<string>} a base64 PNG (as result of a Promise)
 */
async function svgToPNG(src) {
    function checkImg(imgEl) {
        // Firefox does not support drawing SVG to canvas unless it has width
        // and height attributes set on the root <svg>.
        return (imgEl.naturalHeight !== 0);
    }
    function toPNGViaCanvas(imgEl) {
        const canvas = document.createElement('canvas');
        canvas.width = imgEl.width;
        canvas.height = imgEl.height;
        canvas.getContext('2d').drawImage(imgEl, 0, 0);
        return canvas.toDataURL('image/png');
    }

    // In case we receive a loaded image and that this image is not problematic,
    // we can convert it to PNG directly.
    if (src instanceof HTMLImageElement) {
        const loadedImgEl = src;
        if (checkImg(loadedImgEl)) {
            return toPNGViaCanvas(loadedImgEl);
        }
        src = loadedImgEl.src;
    }

    // At this point, we either did not receive a loaded image or the received
    // loaded image is problematic => we have to do some asynchronous code.
    return new Promise(resolve => {
        const imgEl = new Image();
        imgEl.onload = () => {
            if (checkImg(imgEl)) {
                resolve(imgEl);
                return;
            }

            // Set arbitrary height on image and attach it to the DOM to force
            // width computation.
            imgEl.height = 1000;
            imgEl.style.opacity = 0;
            document.body.appendChild(imgEl);

            const request = new XMLHttpRequest();
            request.open('GET', imgEl.src, true);
            request.onload = () => {
                // Convert the data URI to a SVG element
                const parser = new DOMParser();
                const result = parser.parseFromString(request.responseText, 'text/xml');
                const svgEl = result.getElementsByTagName("svg")[0];

                // Add the attributes Firefox needs and remove the image from
                // the DOM.
                svgEl.setAttribute('width', imgEl.width);
                svgEl.setAttribute('height', imgEl.height);
                imgEl.remove();

                // Convert the SVG element to a data URI
                const svg64 = btoa(new XMLSerializer().serializeToString(svgEl));
                const finalImg = new Image();
                finalImg.onload = () => {
                    resolve(finalImg);
                };
                finalImg.src = `data:image/svg+xml;base64,${svg64}`;
            };
            request.send();
        };
        imgEl.src = src;
    }).then(loadedImgEl => toPNGViaCanvas(loadedImgEl));
}

/**
 * Generates a Google Maps URL based on the given parameter.
 *
 * @param {DOMStringMap} dataset
 * @returns {string} a Google Maps URL
 */
function generateGMapLink(dataset) {
    return 'https://maps.google.com/maps?q=' + encodeURIComponent(dataset.mapAddress)
            + '&t=' + encodeURIComponent(dataset.mapType)
            + '&z=' + encodeURIComponent(dataset.mapZoom)
            + '&ie=UTF8&iwloc=&output=embed';
}

/**
 * Returns the parsed data coming from the data-for element for the given form.
 *
 * @param {string} formId
 * @returns {Object|undefined} the parsed data
 */
function getParsedDataFor(formId) {
    const dataForEl = document.querySelector(`[data-for='${formId}']`);
    if (!dataForEl) {
        return;
    }
    return JSON.parse(dataForEl.dataset.values
        // replaces `True` by `true` if they are after `,` or `:` or `[`
        .replace(/([,:\[]\s*)True/g, '$1true')
        // replaces `False` and `None` by `""` if they are after `,` or `:` or `[`
        .replace(/([,:\[]\s*)(False|None)/g, '$1""')
        // replaces the `'` by `"` if they are before `,` or `:` or `]` or `}`
        .replace(/'(\s*[,:\]}])/g, '"$1')
        // replaces the `'` by `"` if they are after `{` or `[` or `,` or `:`
        .replace(/([{\[:,]\s*)'/g, '$1"')
    );
}

/**
 * Deep clones children or parses a string into elements, with or without
 * <script> elements.
 *
 * @param {DocumentFragment|HTMLElement|String} content
 * @param {Boolean} [keepScripts=false] - whether to keep script tags or not.
 * @returns {DocumentFragment}
 */
function cloneContentEls(content, keepScripts = false) {
    let copyFragment;
    if (typeof content === "string") {
        copyFragment = new Range().createContextualFragment(content);
    } else {
        copyFragment = new DocumentFragment();
        const els = [...content.children].map(el => el.cloneNode(true));
        copyFragment.append(...els);
    }
    if (!keepScripts) {
        copyFragment.querySelectorAll("script").forEach(scriptEl => scriptEl.remove());
    }
    return copyFragment;
}

return {
    loadAnchors: loadAnchors,
    autocompleteWithPages: autocompleteWithPages,
    onceAllImagesLoaded: onceAllImagesLoaded,
    prompt: prompt,
    sendRequest: sendRequest,
    websiteDomain: websiteDomain,
    svgToPNG: svgToPNG,
    generateGMapLink: generateGMapLink,
    getParsedDataFor: getParsedDataFor,
    cloneContentEls: cloneContentEls,
};
});
