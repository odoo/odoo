/** @odoo-module **/

// Redefine the getRangeAt function in order to avoid an error appearing
// sometimes when an input element is focused on Firefox.
// The error happens because the range returned by getRangeAt is "restricted".
// Ex: Range { commonAncestorContainer: Restricted, startContainer: Restricted,
// startOffset: 0, endContainer: Restricted, endOffset: 0, collapsed: true }
// The solution consists in detecting when the range is restricted and then
// redefining it manually based on the current selection.
const originalGetRangeAt = Selection.prototype.getRangeAt;
Selection.prototype.getRangeAt = function () {
    let range = originalGetRangeAt.apply(this, arguments);
    // Check if the range is restricted
    if (range.startContainer && !Object.getPrototypeOf(range.startContainer)) {
        // Define the range manually based on the selection
        range = document.createRange();
        range.setStart(this.anchorNode, 0);
        range.setEnd(this.focusNode, 0);
    }
    return range;
};
