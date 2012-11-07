/** 
 * Selection Handles Plugin
 *
 *
 * Options
 *  show - True enables the handles plugin.
 *  drag - Left and Right drag handles
 *  scroll - Scrolling handle
 */
(function () {

function isLeftClick (e, type) {
  return (e.which ? (e.which === 1) : (e.button === 0 || e.button === 1));
}

function boundX(x, graph) {
  return Math.min(Math.max(0, x), graph.plotWidth - 1);
}

function boundY(y, graph) {
  return Math.min(Math.max(0, y), graph.plotHeight);
}

var
  D = Flotr.DOM,
  E = Flotr.EventAdapter,
  _ = Flotr._;


Flotr.addPlugin('selection', {

  options: {
    pinchOnly: null,       // Only select on pinch
    mode: null,            // => one of null, 'x', 'y' or 'xy'
    color: '#B6D9FF',      // => selection box color
    fps: 20                // => frames-per-second
  },

  callbacks: {
    'flotr:mouseup' : function (event) {

      var
        options = this.options.selection,
        selection = this.selection,
        pointer = this.getEventPosition(event);

      if (!options || !options.mode) return;
      if (selection.interval) clearInterval(selection.interval);

      if (this.multitouches) {
        selection.updateSelection();
      } else
      if (!options.pinchOnly) {
        selection.setSelectionPos(selection.selection.second, pointer);
      }
      selection.clearSelection();

      if(selection.selecting && selection.selectionIsSane()){
        selection.drawSelection();
        selection.fireSelectEvent();
        this.ignoreClick = true;
      }
    },
    'flotr:mousedown' : function (event) {

      var
        options = this.options.selection,
        selection = this.selection,
        pointer = this.getEventPosition(event);

      if (!options || !options.mode) return;
      if (!options.mode || (!isLeftClick(event) && _.isUndefined(event.touches))) return;
      if (!options.pinchOnly) selection.setSelectionPos(selection.selection.first, pointer);
      if (selection.interval) clearInterval(selection.interval);

      this.lastMousePos.pageX = null;
      selection.selecting = false;
      selection.interval = setInterval(
        _.bind(selection.updateSelection, this),
        1000 / options.fps
      );
    },
    'flotr:destroy' : function (event) {
      clearInterval(this.selection.interval);
    }
  },

  // TODO This isn't used.  Maybe it belongs in the draw area and fire select event methods?
  getArea: function() {

    var s = this.selection.selection,
      first = s.first,
      second = s.second;

    return {
      x1: Math.min(first.x, second.x),
      x2: Math.max(first.x, second.x),
      y1: Math.min(first.y, second.y),
      y2: Math.max(first.y, second.y)
    };
  },

  selection: {first: {x: -1, y: -1}, second: {x: -1, y: -1}},
  prevSelection: null,
  interval: null,

  /**
   * Fires the 'flotr:select' event when the user made a selection.
   */
  fireSelectEvent: function(name){
    var a = this.axes,
        s = this.selection.selection,
        x1, x2, y1, y2;

    name = name || 'select';

    x1 = a.x.p2d(s.first.x);
    x2 = a.x.p2d(s.second.x);
    y1 = a.y.p2d(s.first.y);
    y2 = a.y.p2d(s.second.y);

    E.fire(this.el, 'flotr:'+name, [{
      x1:Math.min(x1, x2), 
      y1:Math.min(y1, y2), 
      x2:Math.max(x1, x2), 
      y2:Math.max(y1, y2),
      xfirst:x1, xsecond:x2, yfirst:y1, ysecond:y2
    }, this]);
  },

  /**
   * Allows the user the manually select an area.
   * @param {Object} area - Object with coordinates to select.
   */
  setSelection: function(area, preventEvent){
    var options = this.options,
      xa = this.axes.x,
      ya = this.axes.y,
      vertScale = ya.scale,
      hozScale = xa.scale,
      selX = options.selection.mode.indexOf('x') != -1,
      selY = options.selection.mode.indexOf('y') != -1,
      s = this.selection.selection;
    
    this.selection.clearSelection();

    s.first.y  = boundY((selX && !selY) ? 0 : (ya.max - area.y1) * vertScale, this);
    s.second.y = boundY((selX && !selY) ? this.plotHeight - 1: (ya.max - area.y2) * vertScale, this);
    s.first.x  = boundX((selY && !selX) ? 0 : area.x1, this);
    s.second.x = boundX((selY && !selX) ? this.plotWidth : area.x2, this);
    
    this.selection.drawSelection();
    if (!preventEvent)
      this.selection.fireSelectEvent();
  },

  /**
   * Calculates the position of the selection.
   * @param {Object} pos - Position object.
   * @param {Event} event - Event object.
   */
  setSelectionPos: function(pos, pointer) {
    var mode = this.options.selection.mode,
        selection = this.selection.selection;

    if(mode.indexOf('x') == -1) {
      pos.x = (pos == selection.first) ? 0 : this.plotWidth;         
    }else{
      pos.x = boundX(pointer.relX, this);
    }

    if (mode.indexOf('y') == -1) {
      pos.y = (pos == selection.first) ? 0 : this.plotHeight - 1;
    }else{
      pos.y = boundY(pointer.relY, this);
    }
  },
  /**
   * Draws the selection box.
   */
  drawSelection: function() {

    this.selection.fireSelectEvent('selecting');

    var s = this.selection.selection,
      octx = this.octx,
      options = this.options,
      plotOffset = this.plotOffset,
      prevSelection = this.selection.prevSelection;
    
    if (prevSelection &&
      s.first.x == prevSelection.first.x &&
      s.first.y == prevSelection.first.y && 
      s.second.x == prevSelection.second.x &&
      s.second.y == prevSelection.second.y) {
      return;
    }

    octx.save();
    octx.strokeStyle = this.processColor(options.selection.color, {opacity: 0.8});
    octx.lineWidth = 1;
    octx.lineJoin = 'miter';
    octx.fillStyle = this.processColor(options.selection.color, {opacity: 0.4});

    this.selection.prevSelection = {
      first: { x: s.first.x, y: s.first.y },
      second: { x: s.second.x, y: s.second.y }
    };

    var x = Math.min(s.first.x, s.second.x),
        y = Math.min(s.first.y, s.second.y),
        w = Math.abs(s.second.x - s.first.x),
        h = Math.abs(s.second.y - s.first.y);

    octx.fillRect(x + plotOffset.left+0.5, y + plotOffset.top+0.5, w, h);
    octx.strokeRect(x + plotOffset.left+0.5, y + plotOffset.top+0.5, w, h);
    octx.restore();
  },

  /**
   * Updates (draws) the selection box.
   */
  updateSelection: function(){
    if (!this.lastMousePos.pageX) return;

    this.selection.selecting = true;

    if (this.multitouches) {
      this.selection.setSelectionPos(this.selection.selection.first,  this.getEventPosition(this.multitouches[0]));
      this.selection.setSelectionPos(this.selection.selection.second,  this.getEventPosition(this.multitouches[1]));
    } else
    if (this.options.selection.pinchOnly) {
      return;
    } else {
      this.selection.setSelectionPos(this.selection.selection.second, this.lastMousePos);
    }

    this.selection.clearSelection();
    
    if(this.selection.selectionIsSane()) {
      this.selection.drawSelection();
    }
  },

  /**
   * Removes the selection box from the overlay canvas.
   */
  clearSelection: function() {
    if (!this.selection.prevSelection) return;
      
    var prevSelection = this.selection.prevSelection,
      lw = 1,
      plotOffset = this.plotOffset,
      x = Math.min(prevSelection.first.x, prevSelection.second.x),
      y = Math.min(prevSelection.first.y, prevSelection.second.y),
      w = Math.abs(prevSelection.second.x - prevSelection.first.x),
      h = Math.abs(prevSelection.second.y - prevSelection.first.y);
    
    this.octx.clearRect(x + plotOffset.left - lw + 0.5,
                        y + plotOffset.top - lw,
                        w + 2 * lw + 0.5,
                        h + 2 * lw + 0.5);
    
    this.selection.prevSelection = null;
  },
  /**
   * Determines whether or not the selection is sane and should be drawn.
   * @return {Boolean} - True when sane, false otherwise.
   */
  selectionIsSane: function(){
    var s = this.selection.selection;
    return Math.abs(s.second.x - s.first.x) >= 5 || 
           Math.abs(s.second.y - s.first.y) >= 5;
  }

});

})();
