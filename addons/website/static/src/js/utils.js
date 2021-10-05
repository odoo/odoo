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
function autocompleteWithPages(self, $input) {
    $input.autocomplete({
        source: function (request, response) {
            if (request.term[0] === '#') {
                loadAnchors(request.term).then(function (anchors) {
                    response(anchors);
                });
            } else {
                return self._rpc({
                    model: 'website',
                    method: 'search_pages',
                    args: [null, request.term],
                    kwargs: {
                        limit: 15,
                    },
                }).then(function (exists) {
                    var rs = _.map(exists, function (r) {
                        return r.loc;
                    });
                    response(rs.sort());
                });
            }
        },
        close: function () {
            self.trigger_up('website_url_chosen');
        },
    });
}

/**
 * @param {jQuery} $element
 */
function onceAllImagesLoaded($element) {
    var defs = _.map($element.find('img').addBack('img'), function (img) {
        if (img.complete) {
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

/**
 * Converts a base64 SVG into a base64 PNG.
 *
 * @param {string|HTMLImageElement} src - an URL to a SVG or a *loaded* image
 *      with such an URL. This allows the call to this method to be potentially
 *      not return a Promise.
 * @param {boolean} [noAsync=false] In case, the given first parameter is a
 *      loaded image, this parameter allows to ignore problematic images and
 *      return a (problematic) PNG result synchronously.
 * @returns {Promise<string>|string} a base64 PNG (as result of a Promise or not)
 */
function svgToPNG(src, noAsync = false) {
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

    // In case we receive a loaded image with the given src and that this image
    // is not problematic, we can convert it to PNG synchronously.
    if (src instanceof HTMLImageElement) {
        const loadedImgEl = src;
        if (noAsync || checkImg(loadedImgEl)) {
            return toPNGViaCanvas(loadedImgEl);
        }
        src = loadedImgEl.src;
    }

    // At this point, we either did not receive a loaded image or the received
    // loaded image is problematic => we have to do some asynchronous code and
    // the function will thus return a Promise.
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

return {
    loadAnchors: loadAnchors,
    autocompleteWithPages: autocompleteWithPages,
    onceAllImagesLoaded: onceAllImagesLoaded,
    prompt: prompt,
    websiteDomain: websiteDomain,
    svgToPNG: svgToPNG,
};
});
