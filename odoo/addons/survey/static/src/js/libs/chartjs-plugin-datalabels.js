/*!
 * chartjs-plugin-datalabels v2.2.0
 * https://chartjs-plugin-datalabels.netlify.app
 * (c) 2017-2022 chartjs-plugin-datalabels contributors
 * Released under the MIT license
 */
(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory(require('chart.js/helpers'), require('chart.js')) :
    typeof define === 'function' && define.amd ? define(['chart.js/helpers', 'chart.js'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, global.ChartDataLabels = factory(global.Chart.helpers, global.Chart));
    })(this, (function (helpers, chart_js) { 'use strict';
    
    var devicePixelRatio = (function() {
      if (typeof window !== 'undefined') {
        if (window.devicePixelRatio) {
          return window.devicePixelRatio;
        }
    
        // devicePixelRatio is undefined on IE10
        // https://stackoverflow.com/a/20204180/8837887
        // https://github.com/chartjs/chartjs-plugin-datalabels/issues/85
        var screen = window.screen;
        if (screen) {
          return (screen.deviceXDPI || 1) / (screen.logicalXDPI || 1);
        }
      }
    
      return 1;
    }());
    
    var utils = {
      // @todo move this in Chart.helpers.toTextLines
      toTextLines: function(inputs) {
        var lines = [];
        var input;
    
        inputs = [].concat(inputs);
        while (inputs.length) {
          input = inputs.pop();
          if (typeof input === 'string') {
            lines.unshift.apply(lines, input.split('\n'));
          } else if (Array.isArray(input)) {
            inputs.push.apply(inputs, input);
          } else if (!helpers.isNullOrUndef(inputs)) {
            lines.unshift('' + input);
          }
        }
    
        return lines;
      },
    
      // @todo move this in Chart.helpers.canvas.textSize
      // @todo cache calls of measureText if font doesn't change?!
      textSize: function(ctx, lines, font) {
        var items = [].concat(lines);
        var ilen = items.length;
        var prev = ctx.font;
        var width = 0;
        var i;
    
        ctx.font = font.string;
    
        for (i = 0; i < ilen; ++i) {
          width = Math.max(ctx.measureText(items[i]).width, width);
        }
    
        ctx.font = prev;
    
        return {
          height: ilen * font.lineHeight,
          width: width
        };
      },
    
      /**
       * Returns value bounded by min and max. This is equivalent to max(min, min(value, max)).
       * @todo move this method in Chart.helpers.bound
       * https://doc.qt.io/qt-5/qtglobal.html#qBound
       */
      bound: function(min, value, max) {
        return Math.max(min, Math.min(value, max));
      },
    
      /**
       * Returns an array of pair [value, state] where state is:
       * * -1: value is only in a0 (removed)
       * *  1: value is only in a1 (added)
       */
      arrayDiff: function(a0, a1) {
        var prev = a0.slice();
        var updates = [];
        var i, j, ilen, v;
    
        for (i = 0, ilen = a1.length; i < ilen; ++i) {
          v = a1[i];
          j = prev.indexOf(v);
    
          if (j === -1) {
            updates.push([v, 1]);
          } else {
            prev.splice(j, 1);
          }
        }
    
        for (i = 0, ilen = prev.length; i < ilen; ++i) {
          updates.push([prev[i], -1]);
        }
    
        return updates;
      },
    
      /**
       * https://github.com/chartjs/chartjs-plugin-datalabels/issues/70
       */
      rasterize: function(v) {
        return Math.round(v * devicePixelRatio) / devicePixelRatio;
      }
    };
    
    function orient(point, origin) {
      var x0 = origin.x;
      var y0 = origin.y;
    
      if (x0 === null) {
        return {x: 0, y: -1};
      }
      if (y0 === null) {
        return {x: 1, y: 0};
      }
    
      var dx = point.x - x0;
      var dy = point.y - y0;
      var ln = Math.sqrt(dx * dx + dy * dy);
    
      return {
        x: ln ? dx / ln : 0,
        y: ln ? dy / ln : -1
      };
    }
    
    function aligned(x, y, vx, vy, align) {
      switch (align) {
      case 'center':
        vx = vy = 0;
        break;
      case 'bottom':
        vx = 0;
        vy = 1;
        break;
      case 'right':
        vx = 1;
        vy = 0;
        break;
      case 'left':
        vx = -1;
        vy = 0;
        break;
      case 'top':
        vx = 0;
        vy = -1;
        break;
      case 'start':
        vx = -vx;
        vy = -vy;
        break;
      case 'end':
        // keep natural orientation
        break;
      default:
        // clockwise rotation (in degree)
        align *= (Math.PI / 180);
        vx = Math.cos(align);
        vy = Math.sin(align);
        break;
      }
    
      return {
        x: x,
        y: y,
        vx: vx,
        vy: vy
      };
    }
    
    // Line clipping (Cohen–Sutherland algorithm)
    // https://en.wikipedia.org/wiki/Cohen–Sutherland_algorithm
    
    var R_INSIDE = 0;
    var R_LEFT = 1;
    var R_RIGHT = 2;
    var R_BOTTOM = 4;
    var R_TOP = 8;
    
    function region(x, y, rect) {
      var res = R_INSIDE;
    
      if (x < rect.left) {
        res |= R_LEFT;
      } else if (x > rect.right) {
        res |= R_RIGHT;
      }
      if (y < rect.top) {
        res |= R_TOP;
      } else if (y > rect.bottom) {
        res |= R_BOTTOM;
      }
    
      return res;
    }
    
    function clipped(segment, area) {
      var x0 = segment.x0;
      var y0 = segment.y0;
      var x1 = segment.x1;
      var y1 = segment.y1;
      var r0 = region(x0, y0, area);
      var r1 = region(x1, y1, area);
      var r, x, y;
    
      // eslint-disable-next-line no-constant-condition
      while (true) {
        if (!(r0 | r1) || (r0 & r1)) {
          // both points inside or on the same side: no clipping
          break;
        }
    
        // at least one point is outside
        r = r0 || r1;
    
        if (r & R_TOP) {
          x = x0 + (x1 - x0) * (area.top - y0) / (y1 - y0);
          y = area.top;
        } else if (r & R_BOTTOM) {
          x = x0 + (x1 - x0) * (area.bottom - y0) / (y1 - y0);
          y = area.bottom;
        } else if (r & R_RIGHT) {
          y = y0 + (y1 - y0) * (area.right - x0) / (x1 - x0);
          x = area.right;
        } else if (r & R_LEFT) {
          y = y0 + (y1 - y0) * (area.left - x0) / (x1 - x0);
          x = area.left;
        }
    
        if (r === r0) {
          x0 = x;
          y0 = y;
          r0 = region(x0, y0, area);
        } else {
          x1 = x;
          y1 = y;
          r1 = region(x1, y1, area);
        }
      }
    
      return {
        x0: x0,
        x1: x1,
        y0: y0,
        y1: y1
      };
    }
    
    function compute$1(range, config) {
      var anchor = config.anchor;
      var segment = range;
      var x, y;
    
      if (config.clamp) {
        segment = clipped(segment, config.area);
      }
    
      if (anchor === 'start') {
        x = segment.x0;
        y = segment.y0;
      } else if (anchor === 'end') {
        x = segment.x1;
        y = segment.y1;
      } else {
        x = (segment.x0 + segment.x1) / 2;
        y = (segment.y0 + segment.y1) / 2;
      }
    
      return aligned(x, y, range.vx, range.vy, config.align);
    }
    
    var positioners = {
      arc: function(el, config) {
        var angle = (el.startAngle + el.endAngle) / 2;
        var vx = Math.cos(angle);
        var vy = Math.sin(angle);
        var r0 = el.innerRadius;
        var r1 = el.outerRadius;
    
        return compute$1({
          x0: el.x + vx * r0,
          y0: el.y + vy * r0,
          x1: el.x + vx * r1,
          y1: el.y + vy * r1,
          vx: vx,
          vy: vy
        }, config);
      },
    
      point: function(el, config) {
        var v = orient(el, config.origin);
        var rx = v.x * el.options.radius;
        var ry = v.y * el.options.radius;
    
        return compute$1({
          x0: el.x - rx,
          y0: el.y - ry,
          x1: el.x + rx,
          y1: el.y + ry,
          vx: v.x,
          vy: v.y
        }, config);
      },
    
      bar: function(el, config) {
        var v = orient(el, config.origin);
        var x = el.x;
        var y = el.y;
        var sx = 0;
        var sy = 0;
    
        if (el.horizontal) {
          x = Math.min(el.x, el.base);
          sx = Math.abs(el.base - el.x);
        } else {
          y = Math.min(el.y, el.base);
          sy = Math.abs(el.base - el.y);
        }
    
        return compute$1({
          x0: x,
          y0: y + sy,
          x1: x + sx,
          y1: y,
          vx: v.x,
          vy: v.y
        }, config);
      },
    
      fallback: function(el, config) {
        var v = orient(el, config.origin);
    
        return compute$1({
          x0: el.x,
          y0: el.y,
          x1: el.x + (el.width || 0),
          y1: el.y + (el.height || 0),
          vx: v.x,
          vy: v.y
        }, config);
      }
    };
    
    var rasterize = utils.rasterize;
    
    function boundingRects(model) {
      var borderWidth = model.borderWidth || 0;
      var padding = model.padding;
      var th = model.size.height;
      var tw = model.size.width;
      var tx = -tw / 2;
      var ty = -th / 2;
    
      return {
        frame: {
          x: tx - padding.left - borderWidth,
          y: ty - padding.top - borderWidth,
          w: tw + padding.width + borderWidth * 2,
          h: th + padding.height + borderWidth * 2
        },
        text: {
          x: tx,
          y: ty,
          w: tw,
          h: th
        }
      };
    }
    
    function getScaleOrigin(el, context) {
      var scale = context.chart.getDatasetMeta(context.datasetIndex).vScale;
    
      if (!scale) {
        return null;
      }
    
      if (scale.xCenter !== undefined && scale.yCenter !== undefined) {
        return {x: scale.xCenter, y: scale.yCenter};
      }
    
      var pixel = scale.getBasePixel();
      return el.horizontal ?
        {x: pixel, y: null} :
        {x: null, y: pixel};
    }
    
    function getPositioner(el) {
      if (el instanceof chart_js.ArcElement) {
        return positioners.arc;
      }
      if (el instanceof chart_js.PointElement) {
        return positioners.point;
      }
      if (el instanceof chart_js.BarElement) {
        return positioners.bar;
      }
      return positioners.fallback;
    }
    
    function drawRoundedRect(ctx, x, y, w, h, radius) {
      var HALF_PI = Math.PI / 2;
    
      if (radius) {
        var r = Math.min(radius, h / 2, w / 2);
        var left = x + r;
        var top = y + r;
        var right = x + w - r;
        var bottom = y + h - r;
    
        ctx.moveTo(x, top);
        if (left < right && top < bottom) {
          ctx.arc(left, top, r, -Math.PI, -HALF_PI);
          ctx.arc(right, top, r, -HALF_PI, 0);
          ctx.arc(right, bottom, r, 0, HALF_PI);
          ctx.arc(left, bottom, r, HALF_PI, Math.PI);
        } else if (left < right) {
          ctx.moveTo(left, y);
          ctx.arc(right, top, r, -HALF_PI, HALF_PI);
          ctx.arc(left, top, r, HALF_PI, Math.PI + HALF_PI);
        } else if (top < bottom) {
          ctx.arc(left, top, r, -Math.PI, 0);
          ctx.arc(left, bottom, r, 0, Math.PI);
        } else {
          ctx.arc(left, top, r, -Math.PI, Math.PI);
        }
        ctx.closePath();
        ctx.moveTo(x, y);
      } else {
        ctx.rect(x, y, w, h);
      }
    }
    
    function drawFrame(ctx, rect, model) {
      var bgColor = model.backgroundColor;
      var borderColor = model.borderColor;
      var borderWidth = model.borderWidth;
    
      if (!bgColor && (!borderColor || !borderWidth)) {
        return;
      }
    
      ctx.beginPath();
    
      drawRoundedRect(
        ctx,
        rasterize(rect.x) + borderWidth / 2,
        rasterize(rect.y) + borderWidth / 2,
        rasterize(rect.w) - borderWidth,
        rasterize(rect.h) - borderWidth,
        model.borderRadius);
    
      ctx.closePath();
    
      if (bgColor) {
        ctx.fillStyle = bgColor;
        ctx.fill();
      }
    
      if (borderColor && borderWidth) {
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = borderWidth;
        ctx.lineJoin = 'miter';
        ctx.stroke();
      }
    }
    
    function textGeometry(rect, align, font) {
      var h = font.lineHeight;
      var w = rect.w;
      var x = rect.x;
      var y = rect.y + h / 2;
    
      if (align === 'center') {
        x += w / 2;
      } else if (align === 'end' || align === 'right') {
        x += w;
      }
    
      return {
        h: h,
        w: w,
        x: x,
        y: y
      };
    }
    
    function drawTextLine(ctx, text, cfg) {
      var shadow = ctx.shadowBlur;
      var stroked = cfg.stroked;
      var x = rasterize(cfg.x);
      var y = rasterize(cfg.y);
      var w = rasterize(cfg.w);
    
      if (stroked) {
        ctx.strokeText(text, x, y, w);
      }
    
      if (cfg.filled) {
        if (shadow && stroked) {
          // Prevent drawing shadow on both the text stroke and fill, so
          // if the text is stroked, remove the shadow for the text fill.
          ctx.shadowBlur = 0;
        }
    
        ctx.fillText(text, x, y, w);
    
        if (shadow && stroked) {
          ctx.shadowBlur = shadow;
        }
      }
    }
    
    function drawText(ctx, lines, rect, model) {
      var align = model.textAlign;
      var color = model.color;
      var filled = !!color;
      var font = model.font;
      var ilen = lines.length;
      var strokeColor = model.textStrokeColor;
      var strokeWidth = model.textStrokeWidth;
      var stroked = strokeColor && strokeWidth;
      var i;
    
      if (!ilen || (!filled && !stroked)) {
        return;
      }
    
      // Adjust coordinates based on text alignment and line height
      rect = textGeometry(rect, align, font);
    
      ctx.font = font.string;
      ctx.textAlign = align;
      ctx.textBaseline = 'middle';
      ctx.shadowBlur = model.textShadowBlur;
      ctx.shadowColor = model.textShadowColor;
    
      if (filled) {
        ctx.fillStyle = color;
      }
      if (stroked) {
        ctx.lineJoin = 'round';
        ctx.lineWidth = strokeWidth;
        ctx.strokeStyle = strokeColor;
      }
    
      for (i = 0, ilen = lines.length; i < ilen; ++i) {
        drawTextLine(ctx, lines[i], {
          stroked: stroked,
          filled: filled,
          w: rect.w,
          x: rect.x,
          y: rect.y + rect.h * i
        });
      }
    }
    
    var Label = function(config, ctx, el, index) {
      var me = this;
    
      me._config = config;
      me._index = index;
      me._model = null;
      me._rects = null;
      me._ctx = ctx;
      me._el = el;
    };
    
    helpers.merge(Label.prototype, {
      /**
       * @private
       */
      _modelize: function(display, lines, config, context) {
        var me = this;
        var index = me._index;
        var font = helpers.toFont(helpers.resolve([config.font, {}], context, index));
        var color = helpers.resolve([config.color, chart_js.defaults.color], context, index);
    
        return {
          align: helpers.resolve([config.align, 'center'], context, index),
          anchor: helpers.resolve([config.anchor, 'center'], context, index),
          area: context.chart.chartArea,
          backgroundColor: helpers.resolve([config.backgroundColor, null], context, index),
          borderColor: helpers.resolve([config.borderColor, null], context, index),
          borderRadius: helpers.resolve([config.borderRadius, 0], context, index),
          borderWidth: helpers.resolve([config.borderWidth, 0], context, index),
          clamp: helpers.resolve([config.clamp, false], context, index),
          clip: helpers.resolve([config.clip, false], context, index),
          color: color,
          display: display,
          font: font,
          lines: lines,
          offset: helpers.resolve([config.offset, 4], context, index),
          opacity: helpers.resolve([config.opacity, 1], context, index),
          origin: getScaleOrigin(me._el, context),
          padding: helpers.toPadding(helpers.resolve([config.padding, 4], context, index)),
          positioner: getPositioner(me._el),
          rotation: helpers.resolve([config.rotation, 0], context, index) * (Math.PI / 180),
          size: utils.textSize(me._ctx, lines, font),
          textAlign: helpers.resolve([config.textAlign, 'start'], context, index),
          textShadowBlur: helpers.resolve([config.textShadowBlur, 0], context, index),
          textShadowColor: helpers.resolve([config.textShadowColor, color], context, index),
          textStrokeColor: helpers.resolve([config.textStrokeColor, color], context, index),
          textStrokeWidth: helpers.resolve([config.textStrokeWidth, 0], context, index)
        };
      },
    
      update: function(context) {
        var me = this;
        var model = null;
        var rects = null;
        var index = me._index;
        var config = me._config;
        var value, label, lines;
    
        // We first resolve the display option (separately) to avoid computing
        // other options in case the label is hidden (i.e. display: false).
        var display = helpers.resolve([config.display, true], context, index);
    
        if (display) {
          value = context.dataset.data[index];
          label = helpers.valueOrDefault(helpers.callback(config.formatter, [value, context]), value);
          lines = helpers.isNullOrUndef(label) ? [] : utils.toTextLines(label);
    
          if (lines.length) {
            model = me._modelize(display, lines, config, context);
            rects = boundingRects(model);
          }
        }
    
        me._model = model;
        me._rects = rects;
      },
    
      geometry: function() {
        return this._rects ? this._rects.frame : {};
      },
    
      rotation: function() {
        return this._model ? this._model.rotation : 0;
      },
    
      visible: function() {
        return this._model && this._model.opacity;
      },
    
      model: function() {
        return this._model;
      },
    
      draw: function(chart, center) {
        var me = this;
        var ctx = chart.ctx;
        var model = me._model;
        var rects = me._rects;
        var area;
    
        if (!this.visible()) {
          return;
        }
    
        ctx.save();
    
        if (model.clip) {
          area = model.area;
          ctx.beginPath();
          ctx.rect(
            area.left,
            area.top,
            area.right - area.left,
            area.bottom - area.top);
          ctx.clip();
        }
    
        ctx.globalAlpha = utils.bound(0, model.opacity, 1);
        ctx.translate(rasterize(center.x), rasterize(center.y));
        ctx.rotate(model.rotation);
    
        drawFrame(ctx, rects.frame, model);
        drawText(ctx, model.lines, rects.text, model);
    
        ctx.restore();
      }
    });
    
    var MIN_INTEGER = Number.MIN_SAFE_INTEGER || -9007199254740991; // eslint-disable-line es/no-number-minsafeinteger
    var MAX_INTEGER = Number.MAX_SAFE_INTEGER || 9007199254740991;  // eslint-disable-line es/no-number-maxsafeinteger
    
    function rotated(point, center, angle) {
      var cos = Math.cos(angle);
      var sin = Math.sin(angle);
      var cx = center.x;
      var cy = center.y;
    
      return {
        x: cx + cos * (point.x - cx) - sin * (point.y - cy),
        y: cy + sin * (point.x - cx) + cos * (point.y - cy)
      };
    }
    
    function projected(points, axis) {
      var min = MAX_INTEGER;
      var max = MIN_INTEGER;
      var origin = axis.origin;
      var i, pt, vx, vy, dp;
    
      for (i = 0; i < points.length; ++i) {
        pt = points[i];
        vx = pt.x - origin.x;
        vy = pt.y - origin.y;
        dp = axis.vx * vx + axis.vy * vy;
        min = Math.min(min, dp);
        max = Math.max(max, dp);
      }
    
      return {
        min: min,
        max: max
      };
    }
    
    function toAxis(p0, p1) {
      var vx = p1.x - p0.x;
      var vy = p1.y - p0.y;
      var ln = Math.sqrt(vx * vx + vy * vy);
    
      return {
        vx: (p1.x - p0.x) / ln,
        vy: (p1.y - p0.y) / ln,
        origin: p0,
        ln: ln
      };
    }
    
    var HitBox = function() {
      this._rotation = 0;
      this._rect = {
        x: 0,
        y: 0,
        w: 0,
        h: 0
      };
    };
    
    helpers.merge(HitBox.prototype, {
      center: function() {
        var r = this._rect;
        return {
          x: r.x + r.w / 2,
          y: r.y + r.h / 2
        };
      },
    
      update: function(center, rect, rotation) {
        this._rotation = rotation;
        this._rect = {
          x: rect.x + center.x,
          y: rect.y + center.y,
          w: rect.w,
          h: rect.h
        };
      },
    
      contains: function(point) {
        var me = this;
        var margin = 1;
        var rect = me._rect;
    
        point = rotated(point, me.center(), -me._rotation);
    
        return !(point.x < rect.x - margin
          || point.y < rect.y - margin
          || point.x > rect.x + rect.w + margin * 2
          || point.y > rect.y + rect.h + margin * 2);
      },
    
      // Separating Axis Theorem
      // https://gamedevelopment.tutsplus.com/tutorials/collision-detection-using-the-separating-axis-theorem--gamedev-169
      intersects: function(other) {
        var r0 = this._points();
        var r1 = other._points();
        var axes = [
          toAxis(r0[0], r0[1]),
          toAxis(r0[0], r0[3])
        ];
        var i, pr0, pr1;
    
        if (this._rotation !== other._rotation) {
          // Only separate with r1 axis if the rotation is different,
          // else it's enough to separate r0 and r1 with r0 axis only!
          axes.push(
            toAxis(r1[0], r1[1]),
            toAxis(r1[0], r1[3])
          );
        }
    
        for (i = 0; i < axes.length; ++i) {
          pr0 = projected(r0, axes[i]);
          pr1 = projected(r1, axes[i]);
    
          if (pr0.max < pr1.min || pr1.max < pr0.min) {
            return false;
          }
        }
    
        return true;
      },
    
      /**
       * @private
       */
      _points: function() {
        var me = this;
        var rect = me._rect;
        var angle = me._rotation;
        var center = me.center();
    
        return [
          rotated({x: rect.x, y: rect.y}, center, angle),
          rotated({x: rect.x + rect.w, y: rect.y}, center, angle),
          rotated({x: rect.x + rect.w, y: rect.y + rect.h}, center, angle),
          rotated({x: rect.x, y: rect.y + rect.h}, center, angle)
        ];
      }
    });
    
    function coordinates(el, model, geometry) {
      var point = model.positioner(el, model);
      var vx = point.vx;
      var vy = point.vy;
    
      if (!vx && !vy) {
        // if aligned center, we don't want to offset the center point
        return {x: point.x, y: point.y};
      }
    
      var w = geometry.w;
      var h = geometry.h;
    
      // take in account the label rotation
      var rotation = model.rotation;
      var dx = Math.abs(w / 2 * Math.cos(rotation)) + Math.abs(h / 2 * Math.sin(rotation));
      var dy = Math.abs(w / 2 * Math.sin(rotation)) + Math.abs(h / 2 * Math.cos(rotation));
    
      // scale the unit vector (vx, vy) to get at least dx or dy equal to
      // w or h respectively (else we would calculate the distance to the
      // ellipse inscribed in the bounding rect)
      var vs = 1 / Math.max(Math.abs(vx), Math.abs(vy));
      dx *= vx * vs;
      dy *= vy * vs;
    
      // finally, include the explicit offset
      dx += model.offset * vx;
      dy += model.offset * vy;
    
      return {
        x: point.x + dx,
        y: point.y + dy
      };
    }
    
    function collide(labels, collider) {
      var i, j, s0, s1;
    
      // IMPORTANT Iterate in the reverse order since items at the end of the
      // list have an higher weight/priority and thus should be less impacted
      // by the overlapping strategy.
    
      for (i = labels.length - 1; i >= 0; --i) {
        s0 = labels[i].$layout;
    
        for (j = i - 1; j >= 0 && s0._visible; --j) {
          s1 = labels[j].$layout;
    
          if (s1._visible && s0._box.intersects(s1._box)) {
            collider(s0, s1);
          }
        }
      }
    
      return labels;
    }
    
    function compute(labels) {
      var i, ilen, label, state, geometry, center, proxy;
    
      // Initialize labels for overlap detection
      for (i = 0, ilen = labels.length; i < ilen; ++i) {
        label = labels[i];
        state = label.$layout;
    
        if (state._visible) {
          // Chart.js 3 removed el._model in favor of getProps(), making harder to
          // abstract reading values in positioners. Also, using string arrays to
          // read values (i.e. var {a,b,c} = el.getProps(["a","b","c"])) would make
          // positioners inefficient in the normal case (i.e. not the final values)
          // and the code a bit ugly, so let's use a Proxy instead.
          proxy = new Proxy(label._el, {get: (el, p) => el.getProps([p], true)[p]});
    
          geometry = label.geometry();
          center = coordinates(proxy, label.model(), geometry);
          state._box.update(center, geometry, label.rotation());
        }
      }
    
      // Auto hide overlapping labels
      return collide(labels, function(s0, s1) {
        var h0 = s0._hidable;
        var h1 = s1._hidable;
    
        if ((h0 && h1) || h1) {
          s1._visible = false;
        } else if (h0) {
          s0._visible = false;
        }
      });
    }
    
    var layout = {
      prepare: function(datasets) {
        var labels = [];
        var i, j, ilen, jlen, label;
    
        for (i = 0, ilen = datasets.length; i < ilen; ++i) {
          for (j = 0, jlen = datasets[i].length; j < jlen; ++j) {
            label = datasets[i][j];
            labels.push(label);
            label.$layout = {
              _box: new HitBox(),
              _hidable: false,
              _visible: true,
              _set: i,
              _idx: label._index
            };
          }
        }
    
        // TODO New `z` option: labels with a higher z-index are drawn
        // of top of the ones with a lower index. Lowest z-index labels
        // are also discarded first when hiding overlapping labels.
        labels.sort(function(a, b) {
          var sa = a.$layout;
          var sb = b.$layout;
    
          return sa._idx === sb._idx
            ? sb._set - sa._set
            : sb._idx - sa._idx;
        });
    
        this.update(labels);
    
        return labels;
      },
    
      update: function(labels) {
        var dirty = false;
        var i, ilen, label, model, state;
    
        for (i = 0, ilen = labels.length; i < ilen; ++i) {
          label = labels[i];
          model = label.model();
          state = label.$layout;
          state._hidable = model && model.display === 'auto';
          state._visible = label.visible();
          dirty |= state._hidable;
        }
    
        if (dirty) {
          compute(labels);
        }
      },
    
      lookup: function(labels, point) {
        var i, state;
    
        // IMPORTANT Iterate in the reverse order since items at the end of
        // the list have an higher z-index, thus should be picked first.
    
        for (i = labels.length - 1; i >= 0; --i) {
          state = labels[i].$layout;
    
          if (state && state._visible && state._box.contains(point)) {
            return labels[i];
          }
        }
    
        return null;
      },
    
      draw: function(chart, labels) {
        var i, ilen, label, state, geometry, center;
    
        for (i = 0, ilen = labels.length; i < ilen; ++i) {
          label = labels[i];
          state = label.$layout;
    
          if (state._visible) {
            geometry = label.geometry();
            center = coordinates(label._el, label.model(), geometry);
            state._box.update(center, geometry, label.rotation());
            label.draw(chart, center);
          }
        }
      }
    };
    
    var formatter = function(value) {
      if (helpers.isNullOrUndef(value)) {
        return null;
      }
    
      var label = value;
      var keys, klen, k;
      if (helpers.isObject(value)) {
        if (!helpers.isNullOrUndef(value.label)) {
          label = value.label;
        } else if (!helpers.isNullOrUndef(value.r)) {
          label = value.r;
        } else {
          label = '';
          keys = Object.keys(value);
          for (k = 0, klen = keys.length; k < klen; ++k) {
            label += (k !== 0 ? ', ' : '') + keys[k] + ': ' + value[keys[k]];
          }
        }
      }
    
      return '' + label;
    };
    
    /**
     * IMPORTANT: make sure to also update tests and TypeScript definition
     * files (`/test/specs/defaults.spec.js` and `/types/options.d.ts`)
     */
    
    var defaults = {
      align: 'center',
      anchor: 'center',
      backgroundColor: null,
      borderColor: null,
      borderRadius: 0,
      borderWidth: 0,
      clamp: false,
      clip: false,
      color: undefined,
      display: true,
      font: {
        family: undefined,
        lineHeight: 1.2,
        size: undefined,
        style: undefined,
        weight: null
      },
      formatter: formatter,
      labels: undefined,
      listeners: {},
      offset: 4,
      opacity: 1,
      padding: {
        top: 4,
        right: 4,
        bottom: 4,
        left: 4
      },
      rotation: 0,
      textAlign: 'start',
      textStrokeColor: undefined,
      textStrokeWidth: 0,
      textShadowBlur: 0,
      textShadowColor: undefined
    };
    
    /**
     * @see https://github.com/chartjs/Chart.js/issues/4176
     */
    
    var EXPANDO_KEY = '$datalabels';
    var DEFAULT_KEY = '$default';
    
    function configure(dataset, options) {
      var override = dataset.datalabels;
      var listeners = {};
      var configs = [];
      var labels, keys;
    
      if (override === false) {
        return null;
      }
      if (override === true) {
        override = {};
      }
    
      options = helpers.merge({}, [options, override]);
      labels = options.labels || {};
      keys = Object.keys(labels);
      delete options.labels;
    
      if (keys.length) {
        keys.forEach(function(key) {
          if (labels[key]) {
            configs.push(helpers.merge({}, [
              options,
              labels[key],
              {_key: key}
            ]));
          }
        });
      } else {
        // Default label if no "named" label defined.
        configs.push(options);
      }
    
      // listeners: {<event-type>: {<label-key>: <fn>}}
      listeners = configs.reduce(function(target, config) {
        helpers.each(config.listeners || {}, function(fn, event) {
          target[event] = target[event] || {};
          target[event][config._key || DEFAULT_KEY] = fn;
        });
    
        delete config.listeners;
        return target;
      }, {});
    
      return {
        labels: configs,
        listeners: listeners
      };
    }
    
    function dispatchEvent(chart, listeners, label, event) {
      if (!listeners) {
        return;
      }
    
      var context = label.$context;
      var groups = label.$groups;
      var callback;
    
      if (!listeners[groups._set]) {
        return;
      }
    
      callback = listeners[groups._set][groups._key];
      if (!callback) {
        return;
      }
    
      if (helpers.callback(callback, [context, event]) === true) {
        // Users are allowed to tweak the given context by injecting values that can be
        // used in scriptable options to display labels differently based on the current
        // event (e.g. highlight an hovered label). That's why we update the label with
        // the output context and schedule a new chart render by setting it dirty.
        chart[EXPANDO_KEY]._dirty = true;
        label.update(context);
      }
    }
    
    function dispatchMoveEvents(chart, listeners, previous, label, event) {
      var enter, leave;
    
      if (!previous && !label) {
        return;
      }
    
      if (!previous) {
        enter = true;
      } else if (!label) {
        leave = true;
      } else if (previous !== label) {
        leave = enter = true;
      }
    
      if (leave) {
        dispatchEvent(chart, listeners.leave, previous, event);
      }
      if (enter) {
        dispatchEvent(chart, listeners.enter, label, event);
      }
    }
    
    function handleMoveEvents(chart, event) {
      var expando = chart[EXPANDO_KEY];
      var listeners = expando._listeners;
      var previous, label;
    
      if (!listeners.enter && !listeners.leave) {
        return;
      }
    
      if (event.type === 'mousemove') {
        label = layout.lookup(expando._labels, event);
      } else if (event.type !== 'mouseout') {
        return;
      }
    
      previous = expando._hovered;
      expando._hovered = label;
      dispatchMoveEvents(chart, listeners, previous, label, event);
    }
    
    function handleClickEvents(chart, event) {
      var expando = chart[EXPANDO_KEY];
      var handlers = expando._listeners.click;
      var label = handlers && layout.lookup(expando._labels, event);
      if (label) {
        dispatchEvent(chart, handlers, label, event);
      }
    }
    
    var plugin = {
      id: 'datalabels',
    
      defaults: defaults,
    
      beforeInit: function(chart) {
        chart[EXPANDO_KEY] = {
          _actives: []
        };
      },
    
      beforeUpdate: function(chart) {
        var expando = chart[EXPANDO_KEY];
        expando._listened = false;
        expando._listeners = {};     // {<event-type>: {<dataset-index>: {<label-key>: <fn>}}}
        expando._datasets = [];      // per dataset labels: [Label[]]
        expando._labels = [];        // layouted labels: Label[]
      },
    
      afterDatasetUpdate: function(chart, args, options) {
        var datasetIndex = args.index;
        var expando = chart[EXPANDO_KEY];
        var labels = expando._datasets[datasetIndex] = [];
        var visible = chart.isDatasetVisible(datasetIndex);
        var dataset = chart.data.datasets[datasetIndex];
        var config = configure(dataset, options);
        var elements = args.meta.data || [];
        var ctx = chart.ctx;
        var i, j, ilen, jlen, cfg, key, el, label;
    
        ctx.save();
    
        for (i = 0, ilen = elements.length; i < ilen; ++i) {
          el = elements[i];
          el[EXPANDO_KEY] = [];
    
          if (visible && el && chart.getDataVisibility(i) && !el.skip) {
            for (j = 0, jlen = config.labels.length; j < jlen; ++j) {
              cfg = config.labels[j];
              key = cfg._key;
    
              label = new Label(cfg, ctx, el, i);
              label.$groups = {
                _set: datasetIndex,
                _key: key || DEFAULT_KEY
              };
              label.$context = {
                active: false,
                chart: chart,
                dataIndex: i,
                dataset: dataset,
                datasetIndex: datasetIndex
              };
    
              label.update(label.$context);
              el[EXPANDO_KEY].push(label);
              labels.push(label);
            }
          }
        }
    
        ctx.restore();
    
        // Store listeners at the chart level and per event type to optimize
        // cases where no listeners are registered for a specific event.
        helpers.merge(expando._listeners, config.listeners, {
          merger: function(event, target, source) {
            target[event] = target[event] || {};
            target[event][args.index] = source[event];
            expando._listened = true;
          }
        });
      },
    
      afterUpdate: function(chart) {
        chart[EXPANDO_KEY]._labels = layout.prepare(chart[EXPANDO_KEY]._datasets);
      },
    
      // Draw labels on top of all dataset elements
      // https://github.com/chartjs/chartjs-plugin-datalabels/issues/29
      // https://github.com/chartjs/chartjs-plugin-datalabels/issues/32
      afterDatasetsDraw: function(chart) {
        layout.draw(chart, chart[EXPANDO_KEY]._labels);
      },
    
      beforeEvent: function(chart, args) {
        // If there is no listener registered for this chart, `listened` will be false,
        // meaning we can immediately ignore the incoming event and avoid useless extra
        // computation for users who don't implement label interactions.
        if (chart[EXPANDO_KEY]._listened) {
          var event = args.event;
          switch (event.type) {
          case 'mousemove':
          case 'mouseout':
            handleMoveEvents(chart, event);
            break;
          case 'click':
            handleClickEvents(chart, event);
            break;
          }
        }
      },
    
      afterEvent: function(chart) {
        var expando = chart[EXPANDO_KEY];
        var previous = expando._actives;
        var actives = expando._actives = chart.getActiveElements();
        var updates = utils.arrayDiff(previous, actives);
        var i, ilen, j, jlen, update, label, labels;
    
        for (i = 0, ilen = updates.length; i < ilen; ++i) {
          update = updates[i];
          if (update[1]) {
            labels = update[0].element[EXPANDO_KEY] || [];
            for (j = 0, jlen = labels.length; j < jlen; ++j) {
              label = labels[j];
              label.$context.active = (update[1] === 1);
              label.update(label.$context);
            }
          }
        }
    
        if (expando._dirty || updates.length) {
          layout.update(expando._labels);
          chart.render();
        }
    
        delete expando._dirty;
      }
    };
    
    return plugin;
    
    }));
