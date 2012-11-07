(function () {

var D = Flotr.DOM;

Flotr.addPlugin('labels', {

  callbacks : {
    'flotr:afterdraw' : function () {
      this.labels.draw();
    }
  },

  draw: function(){
    // Construct fixed width label boxes, which can be styled easily.
    var
      axis, tick, left, top, xBoxWidth,
      radius, sides, coeff, angle,
      div, i, html = '',
      noLabels = 0,
      options  = this.options,
      ctx      = this.ctx,
      a        = this.axes,
      style    = { size: options.fontSize };

    for (i = 0; i < a.x.ticks.length; ++i){
      if (a.x.ticks[i].label) { ++noLabels; }
    }
    xBoxWidth = this.plotWidth / noLabels;

    if (options.grid.circular) {
      ctx.save();
      ctx.translate(this.plotOffset.left + this.plotWidth / 2,
          this.plotOffset.top + this.plotHeight / 2);

      radius = this.plotHeight * options.radar.radiusRatio / 2 + options.fontSize;
      sides  = this.axes.x.ticks.length;
      coeff  = 2 * (Math.PI / sides);
      angle  = -Math.PI / 2;

      drawLabelCircular(this, a.x, false);
      drawLabelCircular(this, a.x, true);
      drawLabelCircular(this, a.y, false);
      drawLabelCircular(this, a.y, true);
      ctx.restore();
    }

    if (!options.HtmlText && this.textEnabled) {
      drawLabelNoHtmlText(this, a.x, 'center', 'top');
      drawLabelNoHtmlText(this, a.x2, 'center', 'bottom');
      drawLabelNoHtmlText(this, a.y, 'right', 'middle');
      drawLabelNoHtmlText(this, a.y2, 'left', 'middle');
    
    } else if ((
        a.x.options.showLabels ||
        a.x2.options.showLabels ||
        a.y.options.showLabels ||
        a.y2.options.showLabels) &&
        !options.grid.circular
      ) {

      html = '';

      drawLabelHtml(this, a.x);
      drawLabelHtml(this, a.x2);
      drawLabelHtml(this, a.y);
      drawLabelHtml(this, a.y2);

      ctx.stroke();
      ctx.restore();
      div = D.create('div');
      D.setStyles(div, {
        fontSize: 'smaller',
        color: options.grid.color
      });
      div.className = 'flotr-labels';
      D.insert(this.el, div);
      D.insert(div, html);
    }

    function drawLabelCircular (graph, axis, minorTicks) {
      var
        ticks   = minorTicks ? axis.minorTicks : axis.ticks,
        isX     = axis.orientation === 1,
        isFirst = axis.n === 1,
        style, offset;

      style = {
        color        : axis.options.color || options.grid.color,
        angle        : Flotr.toRad(axis.options.labelsAngle),
        textBaseline : 'middle'
      };

      for (i = 0; i < ticks.length &&
          (minorTicks ? axis.options.showMinorLabels : axis.options.showLabels); ++i){
        tick = ticks[i];
        tick.label += '';
        if (!tick.label || !tick.label.length) { continue; }

        x = Math.cos(i * coeff + angle) * radius;
        y = Math.sin(i * coeff + angle) * radius;

        style.textAlign = isX ? (Math.abs(x) < 0.1 ? 'center' : (x < 0 ? 'right' : 'left')) : 'left';

        Flotr.drawText(
          ctx, tick.label,
          isX ? x : 3,
          isX ? y : -(axis.ticks[i].v / axis.max) * (radius - options.fontSize),
          style
        );
      }
    }

    function drawLabelNoHtmlText (graph, axis, textAlign, textBaseline)  {
      var
        isX     = axis.orientation === 1,
        isFirst = axis.n === 1,
        style, offset;

      style = {
        color        : axis.options.color || options.grid.color,
        textAlign    : textAlign,
        textBaseline : textBaseline,
        angle : Flotr.toRad(axis.options.labelsAngle)
      };
      style = Flotr.getBestTextAlign(style.angle, style);

      for (i = 0; i < axis.ticks.length && continueShowingLabels(axis); ++i) {

        tick = axis.ticks[i];
        if (!tick.label || !tick.label.length) { continue; }

        offset = axis.d2p(tick.v);
        if (offset < 0 ||
            offset > (isX ? graph.plotWidth : graph.plotHeight)) { continue; }

        Flotr.drawText(
          ctx, tick.label,
          leftOffset(graph, isX, isFirst, offset),
          topOffset(graph, isX, isFirst, offset),
          style
        );

        // Only draw on axis y2
        if (!isX && !isFirst) {
          ctx.save();
          ctx.strokeStyle = style.color;
          ctx.beginPath();
          ctx.moveTo(graph.plotOffset.left + graph.plotWidth - 8, graph.plotOffset.top + axis.d2p(tick.v));
          ctx.lineTo(graph.plotOffset.left + graph.plotWidth, graph.plotOffset.top + axis.d2p(tick.v));
          ctx.stroke();
          ctx.restore();
        }
      }

      function continueShowingLabels (axis) {
        return axis.options.showLabels && axis.used;
      }
      function leftOffset (graph, isX, isFirst, offset) {
        return graph.plotOffset.left +
          (isX ? offset :
            (isFirst ?
              -options.grid.labelMargin :
              options.grid.labelMargin + graph.plotWidth));
      }
      function topOffset (graph, isX, isFirst, offset) {
        return graph.plotOffset.top +
          (isX ? options.grid.labelMargin : offset) +
          ((isX && isFirst) ? graph.plotHeight : 0);
      }
    }

    function drawLabelHtml (graph, axis) {
      var
        isX     = axis.orientation === 1,
        isFirst = axis.n === 1,
        name = '',
        left, style, top,
        offset = graph.plotOffset;

      if (!isX && !isFirst) {
        ctx.save();
        ctx.strokeStyle = axis.options.color || options.grid.color;
        ctx.beginPath();
      }

      if (axis.options.showLabels && (isFirst ? true : axis.used)) {
        for (i = 0; i < axis.ticks.length; ++i) {
          tick = axis.ticks[i];
          if (!tick.label || !tick.label.length ||
              ((isX ? offset.left : offset.top) + axis.d2p(tick.v) < 0) ||
              ((isX ? offset.left : offset.top) + axis.d2p(tick.v) > (isX ? graph.canvasWidth : graph.canvasHeight))) {
            continue;
          }
          top = offset.top +
            (isX ?
              ((isFirst ? 1 : -1 ) * (graph.plotHeight + options.grid.labelMargin)) :
              axis.d2p(tick.v) - axis.maxLabel.height / 2);
          left = isX ? (offset.left + axis.d2p(tick.v) - xBoxWidth / 2) : 0;

          name = '';
          if (i === 0) {
            name = ' first';
          } else if (i === axis.ticks.length - 1) {
            name = ' last';
          }
          name += isX ? ' flotr-grid-label-x' : ' flotr-grid-label-y';

          html += [
            '<div style="position:absolute; text-align:' + (isX ? 'center' : 'right') + '; ',
            'top:' + top + 'px; ',
            ((!isX && !isFirst) ? 'right:' : 'left:') + left + 'px; ',
            'width:' + (isX ? xBoxWidth : ((isFirst ? offset.left : offset.right) - options.grid.labelMargin)) + 'px; ',
            axis.options.color ? ('color:' + axis.options.color + '; ') : ' ',
            '" class="flotr-grid-label' + name + '">' + tick.label + '</div>'
          ].join(' ');
          
          if (!isX && !isFirst) {
            ctx.moveTo(offset.left + graph.plotWidth - 8, offset.top + axis.d2p(tick.v));
            ctx.lineTo(offset.left + graph.plotWidth, offset.top + axis.d2p(tick.v));
          }
        }
      }
    }
  }

});
})();
