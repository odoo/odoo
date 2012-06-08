/** Gantt
 * Base on data in form [s,y,d] where:
 * y - executor or simply y value
 * s - task start value
 * d - task duration
 * **/
Flotr.addType('gantt', {
  options: {
    show: false,           // => setting to true will show gantt, false will hide
    lineWidth: 2,          // => in pixels
    barWidth: 1,           // => in units of the x axis
    fill: true,            // => true to fill the area from the line to the x axis, false for (transparent) no fill
    fillColor: null,       // => fill color
    fillOpacity: 0.4,      // => opacity of the fill color, set to 1 for a solid fill, 0 hides the fill
    centered: true         // => center the bars to their x axis value
  },
  /**
   * Draws gantt series in the canvas element.
   * @param {Object} series - Series with options.gantt.show = true.
   */
  draw: function(series) {
    var ctx = this.ctx,
      bw = series.gantt.barWidth,
      lw = Math.min(series.gantt.lineWidth, bw);
    
    ctx.save();
    ctx.translate(this.plotOffset.left, this.plotOffset.top);
    ctx.lineJoin = 'miter';

    /**
     * @todo linewidth not interpreted the right way.
     */
    ctx.lineWidth = lw;
    ctx.strokeStyle = series.color;
    
    ctx.save();
    this.gantt.plotShadows(series, bw, 0, series.gantt.fill);
    ctx.restore();
    
    if(series.gantt.fill){
      var color = series.gantt.fillColor || series.color;
      ctx.fillStyle = this.processColor(color, {opacity: series.gantt.fillOpacity});
    }
    
    this.gantt.plot(series, bw, 0, series.gantt.fill);
    ctx.restore();
  },
  plot: function(series, barWidth, offset, fill){
    var data = series.data;
    if(data.length < 1) return;
    
    var xa = series.xaxis,
        ya = series.yaxis,
        ctx = this.ctx, i;

    for(i = 0; i < data.length; i++){
      var y = data[i][0],
          s = data[i][1],
          d = data[i][2],
          drawLeft = true, drawTop = true, drawRight = true;
      
      if (s === null || d === null) continue;

      var left = s, 
          right = s + d,
          bottom = y - (series.gantt.centered ? barWidth/2 : 0), 
          top = y + barWidth - (series.gantt.centered ? barWidth/2 : 0);
      
      if(right < xa.min || left > xa.max || top < ya.min || bottom > ya.max)
        continue;

      if(left < xa.min){
        left = xa.min;
        drawLeft = false;
      }

      if(right > xa.max){
        right = xa.max;
        if (xa.lastSerie != series)
          drawTop = false;
      }

      if(bottom < ya.min)
        bottom = ya.min;

      if(top > ya.max){
        top = ya.max;
        if (ya.lastSerie != series)
          drawTop = false;
      }
      
      /**
       * Fill the bar.
       */
      if(fill){
        ctx.beginPath();
        ctx.moveTo(xa.d2p(left), ya.d2p(bottom) + offset);
        ctx.lineTo(xa.d2p(left), ya.d2p(top) + offset);
        ctx.lineTo(xa.d2p(right), ya.d2p(top) + offset);
        ctx.lineTo(xa.d2p(right), ya.d2p(bottom) + offset);
        ctx.fill();
        ctx.closePath();
      }

      /**
       * Draw bar outline/border.
       */
      if(series.gantt.lineWidth && (drawLeft || drawRight || drawTop)){
        ctx.beginPath();
        ctx.moveTo(xa.d2p(left), ya.d2p(bottom) + offset);
        
        ctx[drawLeft ?'lineTo':'moveTo'](xa.d2p(left), ya.d2p(top) + offset);
        ctx[drawTop  ?'lineTo':'moveTo'](xa.d2p(right), ya.d2p(top) + offset);
        ctx[drawRight?'lineTo':'moveTo'](xa.d2p(right), ya.d2p(bottom) + offset);
                 
        ctx.stroke();
        ctx.closePath();
      }
    }
  },
  plotShadows: function(series, barWidth, offset){
    var data = series.data;
    if(data.length < 1) return;
    
    var i, y, s, d,
        xa = series.xaxis,
        ya = series.yaxis,
        ctx = this.ctx,
        sw = this.options.shadowSize;
    
    for(i = 0; i < data.length; i++){
      y = data[i][0];
      s = data[i][1];
      d = data[i][2];
        
      if (s === null || d === null) continue;
            
      var left = s, 
          right = s + d,
          bottom = y - (series.gantt.centered ? barWidth/2 : 0), 
          top = y + barWidth - (series.gantt.centered ? barWidth/2 : 0);
 
      if(right < xa.min || left > xa.max || top < ya.min || bottom > ya.max)
        continue;
      
      if(left < xa.min)   left = xa.min;
      if(right > xa.max)  right = xa.max;
      if(bottom < ya.min) bottom = ya.min;
      if(top > ya.max)    top = ya.max;
      
      var width =  xa.d2p(right)-xa.d2p(left)-((xa.d2p(right)+sw <= this.plotWidth) ? 0 : sw);
      var height = ya.d2p(bottom)-ya.d2p(top)-((ya.d2p(bottom)+sw <= this.plotHeight) ? 0 : sw );
      
      ctx.fillStyle = 'rgba(0,0,0,0.05)';
      ctx.fillRect(Math.min(xa.d2p(left)+sw, this.plotWidth), Math.min(ya.d2p(top)+sw, this.plotHeight), width, height);
    }
  },
  extendXRange: function(axis) {
    if(axis.options.max === null){
      var newmin = axis.min,
          newmax = axis.max,
          i, j, x, s, g,
          stackedSumsPos = {},
          stackedSumsNeg = {},
          lastSerie = null;

      for(i = 0; i < this.series.length; ++i){
        s = this.series[i];
        g = s.gantt;
        
        if(g.show && s.xaxis == axis) {
            for (j = 0; j < s.data.length; j++) {
              if (g.show) {
                y = s.data[j][0]+'';
                stackedSumsPos[y] = Math.max((stackedSumsPos[y] || 0), s.data[j][1]+s.data[j][2]);
                lastSerie = s;
              }
            }
            for (j in stackedSumsPos) {
              newmax = Math.max(stackedSumsPos[j], newmax);
            }
        }
      }
      axis.lastSerie = lastSerie;
      axis.max = newmax;
      axis.min = newmin;
    }
  },
  extendYRange: function(axis){
    if(axis.options.max === null){
      var newmax = Number.MIN_VALUE,
          newmin = Number.MAX_VALUE,
          i, j, s, g,
          stackedSumsPos = {},
          stackedSumsNeg = {},
          lastSerie = null;
                  
      for(i = 0; i < this.series.length; ++i){
        s = this.series[i];
        g = s.gantt;
        
        if (g.show && !s.hide && s.yaxis == axis) {
          var datamax = Number.MIN_VALUE, datamin = Number.MAX_VALUE;
          for(j=0; j < s.data.length; j++){
            datamax = Math.max(datamax,s.data[j][0]);
            datamin = Math.min(datamin,s.data[j][0]);
          }
            
          if (g.centered) {
            newmax = Math.max(datamax + 0.5, newmax);
            newmin = Math.min(datamin - 0.5, newmin);
          }
        else {
          newmax = Math.max(datamax + 1, newmax);
            newmin = Math.min(datamin, newmin);
          }
          // For normal horizontal bars
          if (g.barWidth + datamax > newmax){
            newmax = axis.max + g.barWidth;
          }
        }
      }
      axis.lastSerie = lastSerie;
      axis.max = newmax;
      axis.min = newmin;
      axis.tickSize = Flotr.getTickSize(axis.options.noTicks, newmin, newmax, axis.options.tickDecimals);
    }
  }
});
