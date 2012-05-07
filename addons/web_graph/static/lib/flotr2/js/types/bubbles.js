/** Bubbles **/
Flotr.addType('bubbles', {
  options: {
    show: false,      // => setting to true will show radar chart, false will hide
    lineWidth: 2,     // => line width in pixels
    fill: true,       // => true to fill the area from the line to the x axis, false for (transparent) no fill
    fillOpacity: 0.4, // => opacity of the fill color, set to 1 for a solid fill, 0 hides the fill
    baseRadius: 2     // => ratio of the radar, against the plot size
  },
  draw : function (options) {
    var
      context     = options.context,
      shadowSize  = options.shadowSize;

    context.save();
    context.lineWidth = options.lineWidth;
    
    // Shadows
    context.fillStyle = 'rgba(0,0,0,0.05)';
    context.strokeStyle = 'rgba(0,0,0,0.05)';
    this.plot(options, shadowSize / 2);
    context.strokeStyle = 'rgba(0,0,0,0.1)';
    this.plot(options, shadowSize / 4);

    // Chart
    context.strokeStyle = options.color;
    context.fillStyle = options.fillStyle;
    this.plot(options);
    
    context.restore();
  },
  plot : function (options, offset) {

    var
      data    = options.data,
      context = options.context,
      geometry,
      i, x, y, z;

    offset = offset || 0;
    
    for (i = 0; i < data.length; ++i){

      geometry = this.getGeometry(data[i], options);

      context.beginPath();
      context.arc(geometry.x + offset, geometry.y + offset, geometry.z, 0, 2 * Math.PI, true);
      context.stroke();
      if (options.fill) context.fill();
      context.closePath();
    }
  },
  getGeometry : function (point, options) {
    return {
      x : options.xScale(point[0]),
      y : options.yScale(point[1]),
      z : point[2] * options.baseRadius
    };
  },
  hit : function (options) {
    var
      data = options.data,
      args = options.args,
      mouse = args[0],
      n = args[1],
      x = mouse.x,
      y = mouse.y,
      geometry,
      dx, dy;

    for (i = data.length; i--;) {
      geometry = this.getGeometry(data[i], options);

      dx = geometry.x - options.xScale(x);
      dy = geometry.y - options.yScale(y);

      if (Math.sqrt(dx * dx + dy * dy) < geometry.z) {
        n.x = data[i][0];
        n.y = data[i][1];
        n.index = i;
        n.seriesIndex = options.index;
      }
    }
  },
  drawHit : function (options) {

    var
      context = options.context,
      geometry = this.getGeometry(options.data[options.args.index], options);

    context.save();
    context.lineWidth = options.lineWidth;
    context.fillStyle = options.fillStyle;
    context.strokeStyle = options.color;
    context.beginPath();
    context.arc(geometry.x, geometry.y, geometry.z, 0, 2 * Math.PI, true);
    context.fill();
    context.stroke();
    context.closePath();
    context.restore();
  },
  clearHit : function (options) {

    var
      context = options.context,
      geometry = this.getGeometry(options.data[options.args.index], options),
      offset = geometry.z + options.lineWidth;

    context.save();
    context.clearRect(
      geometry.x - offset, 
      geometry.y - offset,
      2 * offset,
      2 * offset
    );
    context.restore();
  }
  // TODO Add a hit calculation method (like pie)
});
