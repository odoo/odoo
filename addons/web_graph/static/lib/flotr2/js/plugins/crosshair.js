(function () {

var D = Flotr.DOM;

Flotr.addPlugin('crosshair', {
  options: {
    mode: null,            // => one of null, 'x', 'y' or 'xy'
    color: '#FF0000',      // => crosshair color
    hideCursor: true       // => hide the cursor when the crosshair is shown
  },
  callbacks: {
    'flotr:mousemove': function(e, pos) {
      if (this.options.crosshair.mode) {
        this.crosshair.clearCrosshair();
        this.crosshair.drawCrosshair(pos);
      }
    }
  },
  /**   
   * Draws the selection box.
   */
  drawCrosshair: function(pos) {
    var octx = this.octx,
      options = this.options.crosshair,
      plotOffset = this.plotOffset,
      x = plotOffset.left + pos.relX + 0.5,
      y = plotOffset.top + pos.relY + 0.5;
    
    if (pos.relX < 0 || pos.relY < 0 || pos.relX > this.plotWidth || pos.relY > this.plotHeight) {
      this.el.style.cursor = null;
      D.removeClass(this.el, 'flotr-crosshair');
      return; 
    }
    
    if (options.hideCursor) {
      this.el.style.cursor = 'none';
      D.addClass(this.el, 'flotr-crosshair');
    }
    
    octx.save();
    octx.strokeStyle = options.color;
    octx.lineWidth = 1;
    octx.beginPath();
    
    if (options.mode.indexOf('x') != -1) {
      octx.moveTo(x, plotOffset.top);
      octx.lineTo(x, plotOffset.top + this.plotHeight);
    }
    
    if (options.mode.indexOf('y') != -1) {
      octx.moveTo(plotOffset.left, y);
      octx.lineTo(plotOffset.left + this.plotWidth, y);
    }
    
    octx.stroke();
    octx.restore();
  },
  /**
   * Removes the selection box from the overlay canvas.
   */
  clearCrosshair: function() {

    var
      plotOffset = this.plotOffset,
      position = this.lastMousePos,
      context = this.octx;

    if (position) {
      context.clearRect(
        position.relX + plotOffset.left,
        plotOffset.top,
        1,
        this.plotHeight + 1
      );
      context.clearRect(
        plotOffset.left,
        position.relY + plotOffset.top,
        this.plotWidth + 1,
        1
      );    
    }
  }
});
})();
