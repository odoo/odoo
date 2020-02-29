define([
    'summernote/core/list',
    'summernote/core/dom',
    'summernote/core/key',
    'summernote/core/agent',
    'summernote/core/range'
], function (list, dom, key, agent, range) {
    // ODOO override: use 0.8.10 version of this, adapted for the old summernote
    // version odoo is using
    var Clipboard = function (handler) {
        /**
         * paste by clipboard event
         *
         * @param {Event} event
         */
        var pasteByEvent = function (event) {
            if (["INPUT", "TEXTAREA"].indexOf(event.target.tagName) !== -1) {
                // ODOO override: from old summernote version
                return;
            }

            var clipboardData = event.originalEvent.clipboardData;
            var layoutInfo = dom.makeLayoutInfo(event.currentTarget || event.target);
            var $editable = layoutInfo.editable();

            if (clipboardData && clipboardData.items && clipboardData.items.length) {
                var item = list.head(clipboardData.items);
                if (item.kind === 'file' && item.type.indexOf('image/') !== -1) {
                    handler.insertImages(layoutInfo, [item.getAsFile()]);
                }
                handler.invoke('editor.afterCommand', $editable);
            }
        };

        this.attach = function (layoutInfo) {
            layoutInfo.editable().on('paste', pasteByEvent);
        };
    };

    return Clipboard;
});
