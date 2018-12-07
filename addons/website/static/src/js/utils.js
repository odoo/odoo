odoo.define('website.utils', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;

/**
 * Allows the given input to propose existing website URLs.
 *
 * @param {ServicesMixin|Widget} self - an element capable to trigger an RPC
 * @param {jQuery} $input
 */
function autocompleteWithPages(self, $input) {
    $input.autocomplete({
        source: function (request, response) {
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
                response(rs);
            });
        },
    });
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
     * @param {Function} [options.init] optional function that takes the `field` (enhanced with a fillWith() method) and the `dialog` as parameters [can return a deferred]
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

    var def = $.Deferred();

    $.when(xmlDef).then(function () {
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
                if (e.which === 13) {
                    e.preventDefault();
                    dialog.find('.btn-primary').trigger('click');
                }
            });
        }
    });

    return def;
}

return {
    autocompleteWithPages: autocompleteWithPages,
    prompt: prompt,
};
});
