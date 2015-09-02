define(['summernote/core/range', 'summernote/core/dom'], function (range, dom) {
  /**
   * History
   * @class
   */
  var History = function ($editable) {
    var stack = [], stackOffset = -1, hasUndo = false;
    var editable = $editable[0];

    var makeSnapshot = function () {
      var rng = range.create();
      var emptyBookmark = {s: {path: [], offset: 0}, e: {path: [], offset: 0}};

      return {
        contents: $editable.html(),
        bookmark: (rng && dom.ancestor(rng.sc, dom.isEditable) ? rng.bookmark(editable) : emptyBookmark)
      };
    };

    var applySnapshot = function (snapshot) {
      if (snapshot.contents !== null) {
        $editable.html(snapshot.contents);
      }
      if (snapshot.bookmark !== null) {
        range.createFromBookmark(editable, snapshot.bookmark).select();
      }
    };

    this.undo = function () {
      if (0 < stackOffset || (stack.length - 1 === stackOffset && hasUndo)) {
        if (stack.length - 1 === stackOffset) {
          this.recordUndo();
        }
        stackOffset--;
        applySnapshot(stack[stackOffset]);
        hasUndo = !!stackOffset;
      }
    };

    this.hasUndo = function () {
        return 0 < stackOffset || hasUndo;
    };

    this.redo = function () {
      if (stack.length - 1 > stackOffset) {
        stackOffset++;
        applySnapshot(stack[stackOffset]);
      }
    };

    this.hasRedo = function () {
        return stack.length - 1 > stackOffset;
    };

    var last;
    this.recordUndo = function () {
      // test event for firefox: remove stack of history because event doesn't exists
      var key = typeof event !== 'undefined' ? event : false;
      if (key && !event.metaKey && !event.ctrlKey && !event.altKey && event.type === "keydown") {
        key = event.type + "-";
        if (event.which === 8 || event.which === 46) key += 'delete';
        else if (event.which === 13) key += 'enter';
        else key += 'other';
        if (key === last) return;
        hasUndo = true;
      }
      last = key;

      // Wash out stack after stackOffset
      if (stack.length > stackOffset+1) {
        stack = stack.slice(0, stackOffset+1);
      }

      if (stack[stackOffset] && stack[stackOffset].contents === $editable.html()) {
        return;
      }

      stackOffset++;

      // Create new snapshot and push it to the end
      stack.push(makeSnapshot());
      return true;
    };

    this.splitNext = function () {
        last = false;
    };

    this.reset = function () {
        last = false;
        stack = [];
        stackOffset = -1;
        this.recordUndo();
    };

    // Create first undo stack
    this.recordUndo();
  };

  return History;
});
