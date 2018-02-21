odoo.define('web.QWeb', function (require) {
"use strict";

var translation = require('web.translation');

var _t = translation._t;

/**
 * @param {boolean} debug
 * @param {Object} default_dict
 * @param {boolean} [enableTranslation=true] if true (this is the default),
 *   the rendering will translate all strings that are not marked with
 *   t-translation=off.  This is useful for the kanban view, which uses a
 *   template which is already translated by the server
 */
function QWeb(debug, default_dict, enableTranslation) {
    if (enableTranslation === undefined) {
        enableTranslation = true;
    }
    var qweb = new QWeb2.Engine();
    qweb.default_dict = _.extend({}, default_dict || {}, {
        '_' : _,
        'JSON': JSON,
        '_t' : translation._t,
        '__debug__': debug,
        'moment': function(date) { return new moment(date); },
        'csrf_token': odoo.csrf_token,
    });
    qweb.debug = debug;
    qweb.preprocess_node = enableTranslation ? preprocess_node : function () {};
    return qweb;
}

function preprocess_node() {
    // Note that 'this' is the Qweb Node
    switch (this.node.nodeType) {
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            // Text and CDATAs
            var translation = this.node.parentNode.attributes['t-translation'];
            if (translation && translation.value === 'off') {
                return;
            }
            var match = /^(\s*)([\s\S]+?)(\s*)$/.exec(this.node.data);
            if (match) {
                this.node.data = match[1] + _t(match[2]) + match[3];
            }
            break;
        case Node.ELEMENT_NODE:
            // Element
            var attr, attrs = ['label', 'title', 'alt', 'placeholder'];
            while ((attr = attrs.pop())) {
                if (this.attributes[attr]) {
                    this.attributes[attr] = _t(this.attributes[attr]);
                }
            }
    }
}

return QWeb;

});
