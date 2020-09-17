odoo.define('web_editor.wysiwyg.translate_attributes', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var JWEditorLib = require('web_editor.jabberwock');

var core = require('web.core');
var _t = core._t;

var AttributeTranslateDialog = Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options, node) {
        this._super(parent, _.extend({
            title: _t("Translate Attribute"),
            buttons: [
                {text: _t("Close"), classes: 'btn-primary', click: this.applyAttributeChanges}
            ],
        }, options || {}));
        this.editor = options.editor;
        this.editorHelpers = options.editorHelpers;
        this.node = node;
        this.translation = $(node).data('translation');
    },
    /**
     * @override
     */
    start: function () {
        var $group = $('<div/>', {class: 'form-group'}).appendTo(this.$el);
        _.each(this.translation, function (node, attr) {
            var $node = $(node);
            var $label = $('<label class="col-form-label"></label>').text(attr);
            var $input = $('<input class="form-control"/>').val($node.html());
            $input.on('change keyup', function () {
                var value = $input.val();
                $node.html(value).trigger('change', node);
                $node.data('$node').attr($node.data('attribute'), value).trigger('translate');
                $node.trigger('change');
            });
            $group.append($label).append($input);
        });
        return this._super.apply(this, arguments);
    },
    /**
     * Apply the attributes changes in the VDocument.
     */
    applyAttributeChanges: function () {
        const attributeChange = () => {
            for (const attributeName of Object.keys(this.translation)) {
                const domNode = this.translation[attributeName];
                const nodes = this.editorHelpers.getNodes(this.node);
                for (const node of nodes) {
                    node.modifiers.get(JWEditorLib.Attributes).set(attributeName, domNode.textContent);
                }
            }
            this.close();
        }
        this.editor.execCommand(attributeChange);
    }
});

return AttributeTranslateDialog;
});
