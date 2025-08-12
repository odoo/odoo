// jQuery extensions
$.extend($.expr[':'], {
    o_savable: function (node, i, m) {
        while (node) {
            if (node.className && typeof node.className === "string") {
                if (node.className.indexOf('o_not_editable') !== -1) {
                    return false;
                }
                if (node.className.indexOf('o_savable') !== -1) {
                    return true;
                }
            }
            node = node.parentNode;
        }
        return false;
    },
});

function firstChild(node) {
    while (node.firstChild) {
        node = node.firstChild;
    }
    return node;
}
function lastChild(node) {
    while (node.lastChild) {
        node = node.lastChild;
    }
    return node;
}
function nodeLength(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return node.nodeValue.length;
    } else {
        return node.childNodes.length;
    }
}

$.fn.extend({
    focusIn: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            const node = firstChild(this[0]);
            range.setStart(node, 0);
            range.setEnd(node, 0);
            selection.addRange(range);
        }
        return this;
    },
    focusInEnd: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            const node = lastChild(this[0]);
            const length = nodeLength(node);

            range.setStart(node, length);
            range.setEnd(node, length);
            selection.addRange(range);
        }
        return this;
    },
    selectContent: function () {
        if (this.length && !this[0].hasChildNodes()) {
            return this.selectElement();
        }
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            range.setStart(this[0].firstChild, 0);
            range.setEnd(this[0].lastChild, this[0].lastChild.length);
            selection.addRange(range);
        }
        return this;
    },
    selectElement: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const element = this[0];
            const parent = element.parentNode;
            const offsetStart = Array.from(parent.childNodes).indexOf(element);

            const range = new Range();
            range.setStart(parent, offsetStart);
            range.setEnd(parent, offsetStart + 1);
            selection.addRange(range);
        }
        return this;
    },
});
