/** 
 * Selection Handles Plugin
 *
 * Depends upon options.selection.mode
 *
 * Options
 *  show - True enables the handles plugin.
 *  drag - Left and Right drag handles
 *  scroll - Scrolling handle
 */
(function () {

var D = Flotr.DOM;

Flotr.addPlugin('handles', {

  options: {
    show: false,
    drag: true,
    scroll: true
  },

  callbacks: {
    'flotr:afterinit': init,
    'flotr:select': handleSelect,
    'flotr:mousedown': reset,
    'flotr:mousemove': mouseMoveHandler
  }

});


function init() {

  var
    options = this.options,
    handles = this.handles,
    el = this.el,
    scroll, left, right, container;

  if (!options.selection.mode || !options.handles.show || 'ontouchstart' in el) return;

  handles.initialized = true;

  container = D.node('<div class="flotr-handles"></div>');
  options = options.handles;

  // Drag handles
  if (options.drag) {
    right = D.node('<div class="flotr-handles-handle flotr-handles-drag flotr-handles-right"></div>');
    left  = D.node('<div class="flotr-handles-handle flotr-handles-drag flotr-handles-left"></div>');
    D.insert(container, right);
    D.insert(container, left);
    D.hide(left);
    D.hide(right);
    handles.left = left;
    handles.right = right;

    this.observe(left, 'mousedown', function () {
      handles.moveHandler = leftMoveHandler;
    });
    this.observe(right, 'mousedown', function () {
      handles.moveHandler = rightMoveHandler;
    });
  }

  // Scroll handle
  if (options.scroll) {
    scroll = D.node('<div class="flotr-handles-handle flotr-handles-scroll"></div>');
    D.insert(container, scroll);
    D.hide(scroll);
    handles.scroll = scroll;
    this.observe(scroll, 'mousedown', function () {
      handles.moveHandler = scrollMoveHandler;
    });
  }

  this.observe(document, 'mouseup', function() {
    handles.moveHandler = null;
  });

  D.insert(el, container);
}


function handleSelect(selection) {

  if (!this.handles.initialized) return;

  var
    handles = this.handles,
    options = this.options.handles,
    left = handles.left,
    right = handles.right,
    scroll = handles.scroll;

  if (options) {
    if (options.drag) {
      positionDrag(this, left, selection.x1);
      positionDrag(this, right, selection.x2);
    }

    if (options.scroll) {
      positionScroll(
        this,
        scroll,
        selection.x1,
        selection.x2
      );
    }
  }
}

function positionDrag(graph, handle, x) {

  D.show(handle);

  var size = D.size(handle),
    l = Math.round(graph.axes.x.d2p(x) - size.width / 2),
    t = (graph.plotHeight - size.height) / 2;

  D.setStyles(handle, {
    'left' : l+'px',
    'top'  : t+'px'
  });
}

function positionScroll(graph, handle, x1, x2) {

  D.show(handle);

  var size = D.size(handle),
    l = Math.round(graph.axes.x.d2p(x1)),
    t = (graph.plotHeight) - size.height / 2,
    w = (graph.axes.x.d2p(x2) - graph.axes.x.d2p(x1));

  D.setStyles(handle, {
    'left' : l+'px',
    'top'  : t+'px',
    'width': w+'px'
  });
}

function reset() {

  if (!this.handles.initialized) return;

  var
    handles = this.handles;
  if (handles) {
    D.hide(handles.left);
    D.hide(handles.right);
    D.hide(handles.scroll);
  }
}

function mouseMoveHandler(e, position) {

  if (!this.handles.initialized) return;
  if (!this.handles.moveHandler) return;

  var
    delta = position.dX,
    selection = this.selection.selection,
    area = this.selection.getArea(),
    handles = this.handles;

  handles.moveHandler(area, delta);
  checkSwap(area, handles);

  this.selection.setSelection(area);
}

function checkSwap (area, handles) {
  var moveHandler = handles.moveHandler;
  if (area.x1 > area.x2) {
    if (moveHandler == leftMoveHandler) {
      moveHandler = rightMoveHandler;
    } else if (moveHandler == rightMoveHandler) {
      moveHandler = leftMoveHandler;
    }
    handles.moveHandler = moveHandler;
  }
}

function leftMoveHandler(area, delta) {
  area.x1 += delta;
}

function rightMoveHandler(area, delta) {
  area.x2 += delta;
}

function scrollMoveHandler(area, delta) {
  area.x1 += delta;
  area.x2 += delta;
}

})();
