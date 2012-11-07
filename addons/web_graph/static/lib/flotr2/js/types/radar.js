/** Radar **/
Flotr.addType('radar', {
  options: {
    show: false,           // => setting to true will show radar chart, false will hide
    lineWidth: 2,          // => line width in pixels
    fill: true,            // => true to fill the area from the line to the x axis, false for (transparent) no fill
    fillOpacity: 0.4,      // => opacity of the fill color, set to 1 for a solid fill, 0 hides the fill
    radiusRatio: 0.90      // => ratio of the radar, against the plot size
  },
  draw : function (options) {
    var
      context = options.context,
      shadowSize = options.shadowSize;

    context.save();
    context.translate(options.width / 2, options.height / 2);
    context.lineWidth = options.lineWidth;
    
    // Shadow
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
      radius  = Math.min(options.height, options.width) * options.radiusRatio / 2,
      step    = 2 * Math.PI / data.length,
      angle   = -Math.PI / 2,
      i, ratio;

    offset = offset || 0;

    context.beginPath();
    for (i = 0; i < data.length; ++i) {
      ratio = data[i][1] / this.max;

      context[i === 0 ? 'moveTo' : 'lineTo'](
        Math.cos(i * step + angle) * radius * ratio + offset,
        Math.sin(i * step + angle) * radius * ratio + offset
      );
    }
    context.closePath();
    if (options.fill) context.fill();
    context.stroke();
  },
  extendYRange : function (axis, data) {
    this.max = Math.max(axis.max, this.max || -Number.MAX_VALUE);
  }
});
