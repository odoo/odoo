odoo.define('web.QWeb', function (require) {
"use strict";

var translation = require('web.translation');

var _t = translation._t;

function QWeb(debug, default_dict) {
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
    qweb.preprocess_node = preprocess_node;
    return qweb;
}

function preprocess_node() {
    // Note that 'this' is the Qweb Node
    var template = this.node;
    while ((template.tagName !== 'templates' && (!template.attributes || !template.attributes['t-translation'])) && template.parentNode) {
        template = template.parentNode;
    }
    var translation = template.attributes['t-translation'];
    if (translation && translation.value === 'off') {
        return;
    }
    switch (this.node.nodeType) {
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            // Text and CDATAs
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
