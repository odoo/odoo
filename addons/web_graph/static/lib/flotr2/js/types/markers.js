/** Markers **/
/**
 * Formats the marker labels.
 * @param {Object} obj - Marker value Object {x:..,y:..}
 * @return {String} Formatted marker string
 */
(function () {

Flotr.defaultMarkerFormatter = function(obj){
  return (Math.round(obj.y*100)/100)+'';
};

Flotr.addType('markers', {
  options: {
    show: false,           // => setting to true will show markers, false will hide
    lineWidth: 1,          // => line width of the rectangle around the marker
    color: '#000000',      // => text color
    fill: false,           // => fill or not the marekers' rectangles
    fillColor: "#FFFFFF",  // => fill color
    fillOpacity: 0.4,      // => fill opacity
    stroke: false,         // => draw the rectangle around the markers
    position: 'ct',        // => the markers position (vertical align: b, m, t, horizontal align: l, c, r)
    verticalMargin: 0,     // => the margin between the point and the text.
    labelFormatter: Flotr.defaultMarkerFormatter,
    fontSize: Flotr.defaultOptions.fontSize,
    stacked: false,        // => true if markers should be stacked
    stackingType: 'b',     // => define staching behavior, (b- bars like, a - area like) (see Issue 125 for details)
    horizontal: false      // => true if markers should be horizontal (For now only in a case on horizontal stacked bars, stacks should be calculated horizontaly)
  },

  // TODO test stacked markers.
  stack : {
      positive : [],
      negative : [],
      values : []
  },

  draw : function (options) {

    var
      data            = options.data,
      context         = options.context,
      stack           = options.stacked ? options.stack : false,
      stackType       = options.stackingType,
      stackOffsetNeg,
      stackOffsetPos,
      stackOffset,
      i, x, y, label;

    context.save();
    context.lineJoin = 'round';
    context.lineWidth = options.lineWidth;
    context.strokeStyle = 'rgba(0,0,0,0.5)';
    context.fillStyle = options.fillStyle;

    function stackPos (a, b) {
      stackOffsetPos = stack.negative[a] || 0;
      stackOffsetNeg = stack.positive[a] || 0;
      if (b > 0) {
        stack.positive[a] = stackOffsetPos + b;
        return stackOffsetPos + b;
      } else {
        stack.negative[a] = stackOffsetNeg + b;
        return stackOffsetNeg + b;
      }
    }

    for (i = 0; i < data.length; ++i) {
    
      x = data[i][0];
      y = data[i][1];
        
      if (stack) {
        if (stackType == 'b') {
          if (options.horizontal) y = stackPos(y, x);
          else x = stackPos(x, y);
        } else if (stackType == 'a') {
          stackOffset = stack.values[x] || 0;
          stack.values[x] = stackOffset + y;
          y = stackOffset + y;
        }
      }

      label = options.labelFormatter({x: x, y: y, index: i, data : data});
      this.plot(options.xScale(x), options.yScale(y), label, options);
    }
    context.restore();
  },
  plot: function(x, y, label, options) {
    var context = options.context;
    if (isImage(label) && !label.complete) {
      throw 'Marker image not loaded.';
    } else {
      this._plot(x, y, label, options);
    }
  },

  _plot: function(x, y, label, options) {
    var context = options.context,
        margin = 2,
        left = x,
        top = y,
        dim;

    if (isImage(label))
      dim = {height : label.height, width: label.width};
    else
      dim = options.text.canvas(label);

    dim.width = Math.floor(dim.width+margin*2);
    dim.height = Math.floor(dim.height+margin*2);

         if (options.position.indexOf('c') != -1) left -= dim.width/2 + margin;
    else if (options.position.indexOf('l') != -1) left -= dim.width;
    
         if (options.position.indexOf('m') != -1) top -= dim.height/2 + margin;
    else if (options.position.indexOf('t') != -1) top -= dim.height + options.verticalMargin;
    else top += options.verticalMargin;
    
    left = Math.floor(left)+0.5;
    top = Math.floor(top)+0.5;
    
    if(options.fill)
      context.fillRect(left, top, dim.width, dim.height);
      
    if(options.stroke)
      context.strokeRect(left, top, dim.width, dim.height);
    
    if (isImage(label))
      context.drawImage(label, left+margin, top+margin);
    else
      Flotr.drawText(context, label, left+margin, top+margin, {textBaseline: 'top', textAlign: 'left', size: options.fontSize, color: options.color});
  }
});

function isImage (i) {
  return typeof i === 'object' && i.constructor && (Image ? true : i.constructor === Image);
}

})();
