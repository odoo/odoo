/** @odoo-module alias=website.prompt **/

import { intersection } from "@web/core/utils/arrays";
import core from "web.core";

const { qweb, _t } = core;

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
     * website.prompt("What... is your quest?").then(function (answer) {
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
    if (typeof _qweb === "undefined") {
        _qweb = 'website.prompt';
    }
    options = Object.assign({
        window_title: '',
        field_name: '',
        'default': '', // dict notation for IE<9
        init: function () {},
        btn_primary_title: _t('Create'),
        btn_secondary_title: _t('Cancel'),
    }, options || {});

    var type = intersection(Object.keys(options), ['input', 'textarea', 'select']);
    type = type.length ? type[0] : 'input';
    options.field_type = type;
    options.field_name = options.field_name || options[type];

    var def = new Promise(function (resolve, reject) {
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

    return def;
}

export default {
    prompt: prompt,
};
