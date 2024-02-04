if (!d3) {
  var d3 = require("d3");
}

var mpld3 = {
  _mpld3IsLoaded: true,
  figures: [],
  plugin_map: {}
};

mpld3.version = "0.5.9";

mpld3.register_plugin = function(name, obj) {
  mpld3.plugin_map[name] = obj;
};

mpld3.remove_figure = function(figid) {
  var element = document.getElementById(figid);
  if (element !== null) {
    element.innerHTML = "";
  }
  for (var i = 0; i < mpld3.figures.length; i++) {
    var fig = mpld3.figures[i];
    if (fig.figid === figid) {
      mpld3.figures.splice(i, 1);
    }
  }
  return true;
};

mpld3.draw_figure = function(figid, spec, process, clearElem) {
  var element = document.getElementById(figid);
  clearElem = typeof clearElem !== "undefined" ? clearElem : false;
  if (clearElem) {
    mpld3.remove_figure(figid);
  }
  if (element === null) {
    throw figid + " is not a valid id";
  }
  var fig = new mpld3.Figure(figid, spec);
  if (process) {
    process(fig, element);
  }
  mpld3.figures.push(fig);
  fig.draw();
  return fig;
};

mpld3.cloneObj = mpld3_cloneObj;

function mpld3_cloneObj(oldObj) {
  var newObj = {};
  for (var key in oldObj) {
    newObj[key] = oldObj[key];
  }
  return newObj;
}

mpld3.boundsToTransform = function(fig, bounds) {
  var width = fig.width;
  var height = fig.height;
  var dx = bounds[1][0] - bounds[0][0];
  var dy = bounds[1][1] - bounds[0][1];
  var x = (bounds[0][0] + bounds[1][0]) / 2;
  var y = (bounds[0][1] + bounds[1][1]) / 2;
  var scale = Math.max(1, Math.min(8, .9 / Math.max(dx / width, dy / height)));
  var translate = [ width / 2 - scale * x, height / 2 - scale * y ];
  return {
    translate: translate,
    scale: scale
  };
};

mpld3.getTransformation = function(transform) {
  var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttributeNS(null, "transform", transform);
  var matrix = g.transform.baseVal.consolidate().matrix;
  var a = matrix.a, b = matrix.b, c = matrix.c, d = matrix.d, e = matrix.e, f = matrix.f;
  var scaleX, scaleY, skewX;
  if (scaleX = Math.sqrt(a * a + b * b)) a /= scaleX, b /= scaleX;
  if (skewX = a * c + b * d) c -= a * skewX, d -= b * skewX;
  if (scaleY = Math.sqrt(c * c + d * d)) c /= scaleY, d /= scaleY, skewX /= scaleY;
  if (a * d < b * c) a = -a, b = -b, skewX = -skewX, scaleX = -scaleX;
  var transformObj = {
    translateX: e,
    translateY: f,
    rotate: Math.atan2(b, a) * 180 / Math.PI,
    skewX: Math.atan(skewX) * 180 / Math.PI,
    scaleX: scaleX,
    scaleY: scaleY
  };
  var transformStr = "" + "translate(" + transformObj.translateX + "," + transformObj.translateY + ")" + "rotate(" + transformObj.rotate + ")" + "skewX(" + transformObj.skewX + ")" + "scale(" + transformObj.scaleX + "," + transformObj.scaleY + ")";
  return transformStr;
};

mpld3.merge_objects = function(_) {
  var output = {};
  var obj;
  for (var i = 0; i < arguments.length; i++) {
    obj = arguments[i];
    for (var attr in obj) {
      output[attr] = obj[attr];
    }
  }
  return output;
};

mpld3.generate_id = function(N, chars) {
  console.warn("mpld3.generate_id is deprecated. " + "Use mpld3.generateId instead.");
  return mpld3_generateId(N, chars);
};

mpld3.generateId = mpld3_generateId;

function mpld3_generateId(N, chars) {
  N = typeof N !== "undefined" ? N : 10;
  chars = typeof chars !== "undefined" ? chars : "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  var id = chars.charAt(Math.round(Math.random() * (chars.length - 11)));
  for (var i = 1; i < N; i++) id += chars.charAt(Math.round(Math.random() * (chars.length - 1)));
  return id;
}

mpld3.get_element = function(id, fig) {
  var figs_to_search, ax, el;
  if (typeof fig === "undefined") {
    figs_to_search = mpld3.figures;
  } else if (typeof fig.length === "undefined") {
    figs_to_search = [ fig ];
  } else {
    figs_to_search = fig;
  }
  for (var i = 0; i < figs_to_search.length; i++) {
    fig = figs_to_search[i];
    if (fig.props.id === id) {
      return fig;
    }
    for (var j = 0; j < fig.axes.length; j++) {
      ax = fig.axes[j];
      if (ax.props.id === id) {
        return ax;
      }
      for (var k = 0; k < ax.elements.length; k++) {
        el = ax.elements[k];
        if (el.props.id === id) {
          return el;
        }
      }
    }
  }
  return null;
};

mpld3.insert_css = function(selector, attributes) {
  var head = document.head || document.getElementsByTagName("head")[0];
  var style = document.createElement("style");
  var css = selector + " {";
  for (var prop in attributes) {
    css += prop + ":" + attributes[prop] + "; ";
  }
  css += "}";
  style.type = "text/css";
  if (style.styleSheet) {
    style.styleSheet.cssText = css;
  } else {
    style.appendChild(document.createTextNode(css));
  }
  head.appendChild(style);
};

mpld3.process_props = function(obj, properties, defaults, required) {
  console.warn("mpld3.process_props is deprecated. " + "Plot elements should derive from mpld3.PlotElement");
  Element.prototype = Object.create(mpld3_PlotElement.prototype);
  Element.prototype.constructor = Element;
  Element.prototype.requiredProps = required;
  Element.prototype.defaultProps = defaults;
  function Element(props) {
    mpld3_PlotElement.call(this, null, props);
  }
  var el = new Element(properties);
  return el.props;
};

mpld3.interpolateDates = mpld3_interpolateDates;

function mpld3_interpolateDates(a, b) {
  var interp = d3.interpolate([ a[0].valueOf(), a[1].valueOf() ], [ b[0].valueOf(), b[1].valueOf() ]);
  return function(t) {
    var i = interp(t);
    return [ new Date(i[0]), new Date(i[1]) ];
  };
}

function isUndefined(x) {
  return typeof x === "undefined";
}

function isUndefinedOrNull(x) {
  return x == null || isUndefined(x);
}

function getMod(L, i) {
  return L.length > 0 ? L[i % L.length] : null;
}

mpld3.path = function() {
  return mpld3_path();
};

function mpld3_path(_) {
  var x = function(d, i) {
    return d[0];
  };
  var y = function(d, i) {
    return d[1];
  };
  var defined = function(d, i) {
    return true;
  };
  var n_vertices = {
    M: 1,
    m: 1,
    L: 1,
    l: 1,
    Q: 2,
    q: 2,
    T: 1,
    t: 1,
    S: 2,
    s: 2,
    C: 3,
    c: 3,
    Z: 0,
    z: 0
  };
  function path(vertices, pathcodes) {
    var functor = function(x) {
      if (typeof x == "function") {
        return x;
      }
      return function() {
        return x;
      };
    };
    var fx = functor(x), fy = functor(y);
    var points = [], segments = [], i_v = 0, i_c = -1, halt = 0, nullpath = false;
    if (!pathcodes) {
      pathcodes = [ "M" ];
      for (var i = 1; i < vertices.length; i++) pathcodes.push("L");
    }
    while (++i_c < pathcodes.length) {
      halt = i_v + n_vertices[pathcodes[i_c]];
      points = [];
      while (i_v < halt) {
        if (defined.call(this, vertices[i_v], i_v)) {
          points.push(fx.call(this, vertices[i_v], i_v), fy.call(this, vertices[i_v], i_v));
          i_v++;
        } else {
          points = null;
          i_v = halt;
        }
      }
      if (!points) {
        nullpath = true;
      } else if (nullpath && points.length > 0) {
        segments.push("M", points[0], points[1]);
        nullpath = false;
      } else {
        segments.push(pathcodes[i_c]);
        segments = segments.concat(points);
      }
    }
    if (i_v != vertices.length) console.warn("Warning: not all vertices used in Path");
    return segments.join(" ");
  }
  path.x = function(_) {
    if (!arguments.length) return x;
    x = _;
    return path;
  };
  path.y = function(_) {
    if (!arguments.length) return y;
    y = _;
    return path;
  };
  path.defined = function(_) {
    if (!arguments.length) return defined;
    defined = _;
    return path;
  };
  path.call = path;
  return path;
}

mpld3.multiscale = mpld3_multiscale;

function mpld3_multiscale(_) {
  var args = Array.prototype.slice.call(arguments, 0);
  var N = args.length;
  function scale(x) {
    args.forEach(function(mapping) {
      x = mapping(x);
    });
    return x;
  }
  scale.domain = function(x) {
    if (!arguments.length) return args[0].domain();
    args[0].domain(x);
    return scale;
  };
  scale.range = function(x) {
    if (!arguments.length) return args[N - 1].range();
    args[N - 1].range(x);
    return scale;
  };
  scale.step = function(i) {
    return args[i];
  };
  return scale;
}

mpld3.icons = {
  reset: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBI\nWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gIcACMoD/OzIwAAAJhJREFUOMtjYKAx4KDUgNsMDAx7\nyNV8i4GB4T8U76VEM8mGYNNMtCH4NBM0hBjNMIwSsMzQ0MamcDkDA8NmQi6xggpUoikwQbIkHk2u\nE0rLI7vCBknBSyxeRDZAE6qHgQkq+ZeBgYERSfFPAoHNDNUDN4BswIRmKgxwEasP2dlsDAwMYlA/\n/mVgYHiBpkkGKscIDaPfVMmuAGnOTaGsXF0MAAAAAElFTkSuQmCC\n",
  move: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBI\nWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gIcACQMfLHBNQAAANZJREFUOMud07FKA0EQBuAviaKB\nlFr7COJrpAyYRlKn8hECEkFEn8ROCCm0sBMRYgh5EgVFtEhsRjiO27vkBoZd/vn5d3b+XcrjFI9q\nxgXWkc8pUjOB93GMd3zgB9d1unjDSxmhWSHQqOJki+MtOuv/b3ZifUqctIrMxwhHuG1gim4Ma5kR\nWuEkXFgU4B0MW1Ho4TeyjX3s4TDq3zn8ALvZ7q5wX9DqLOHCDA95cFBAnOO1AL/ZdNopgY3fQcqF\nyriMe37hM9w521ZkkvlMo7o/8g7nZYQ/QDctp1nTCf0AAAAASUVORK5CYII=\n",
  zoom: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBI\nWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gMPDiIRPL/2oQAAANBJREFUOMvF0b9KgzEcheHHVnCT\nKoI4uXbtLXgB3oJDJxevw1VwkoJ/NjepQ2/BrZRCx0ILFURQKV2kyOeSQpAmn7WDB0Lg955zEhLy\n2scdXlBggits+4WOQqjAJ3qYR7NGLrwXGU9+sGbEtlIF18FwmuBngZ+nCt6CIacC3Rx8LSl4xzgF\nn0tusBn4UyVhuA/7ZYIv5g+pE3ail25hN/qdmzCfpsJVjKKCZesDBwtzrAqGOMQj6vhCDRsY4ALH\nmOVObltR/xeG/jph6OD2r+Fv5lZBWEhMx58AAAAASUVORK5CYII=\n",
  brush: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBI\nWXMAAEQkAABEJAFAZ8RUAAAAB3RJTUUH3gMCEiQKB9YaAgAAAWtJREFUOMuN0r1qVVEQhuFn700k\nnfEvBq0iNiIiOKXgH4KCaBeIhWARK/EibLwFCwVLjyAWaQzRGG9grC3URkHUBKKgRuWohWvL5pjj\nyTSLxcz7rZlZHyMiItqzFxGTEVF18/UoODNFxDIO4x12dkXqTcBPsCUzD+AK3ndFqhHwEsYz82gn\nN4dbmMRK9R/4KY7jAvbiWmYeHBT5Z4QCP8J1rGAeN3GvU3Mbl/Gq3qCDcxjLzOV+v78fq/iFIxFx\nPyJ2lNJpfBy2g59YzMyzEbEVLzGBJjOriLiBq5gaJrCIU3hcRCbwAtuwjm/Yg/V6I9NgDA1OR8RC\nZq6Vcd7iUwtn5h8fdMBdETGPE+Xe4ExELDRNs4bX2NfCUHe+7UExyfkCP8MhzOA7PuAkvrbwXyNF\nxF3MDqxiqlhXC7SPdaOKiN14g0u4g3H0MvOiTUSNY3iemb0ywmfMdfYyUmAJ2yPiBx6Wr/oy2Oqw\n+A1SupBzAOuE/AAAAABJRU5ErkJggg==\n"
};

mpld3.Grid = mpld3_Grid;

mpld3_Grid.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Grid.prototype.constructor = mpld3_Grid;

mpld3_Grid.prototype.requiredProps = [ "xy" ];

mpld3_Grid.prototype.defaultProps = {
  color: "gray",
  dasharray: "2,2",
  alpha: "0.5",
  nticks: 10,
  gridOn: true,
  tickvalues: null,
  zorder: 0
};

function mpld3_Grid(ax, prop) {
  mpld3_PlotElement.call(this, ax, prop);
  this.cssclass = "mpld3-" + this.props.xy + "grid";
  if (this.props.xy == "x") {
    this.transform = "translate(0," + this.ax.height + ")";
    this.position = "bottom";
    this.scale = this.ax.xdom;
    this.tickSize = -this.ax.height;
  } else if (this.props.xy == "y") {
    this.transform = "translate(0,0)";
    this.position = "left";
    this.scale = this.ax.ydom;
    this.tickSize = -this.ax.width;
  } else {
    throw "unrecognized grid xy specifier: should be 'x' or 'y'";
  }
}

mpld3_Grid.prototype.draw = function() {
  var scaleMethod = {
    left: "axisLeft",
    right: "axisRight",
    top: "axisTop",
    bottom: "axisBottom"
  }[this.position];
  this.grid = d3[scaleMethod](this.scale).ticks(this.props.nticks).tickValues(this.props.tickvalues).tickSize(this.tickSize, 0, 0).tickFormat("");
  this.elem = this.ax.axes.append("g").attr("class", this.cssclass).attr("transform", this.transform).call(this.grid);
  mpld3.insert_css("div#" + this.ax.fig.figid + " ." + this.cssclass + " .tick", {
    stroke: this.props.color,
    "stroke-dasharray": this.props.dasharray,
    "stroke-opacity": this.props.alpha
  });
  mpld3.insert_css("div#" + this.ax.fig.figid + " ." + this.cssclass + " path", {
    "stroke-width": 0
  });
  mpld3.insert_css("div#" + this.ax.fig.figid + " ." + this.cssclass + " .domain", {
    "pointer-events": "none"
  });
};

mpld3_Grid.prototype.zoomed = function(transform) {
  if (transform) {
    if (this.props.xy == "x") {
      this.elem.call(this.grid.scale(transform.rescaleX(this.scale)));
    } else {
      this.elem.call(this.grid.scale(transform.rescaleY(this.scale)));
    }
  } else {
    this.elem.call(this.grid);
  }
};

mpld3.Axis = mpld3_Axis;

mpld3_Axis.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Axis.prototype.constructor = mpld3_Axis;

mpld3_Axis.prototype.requiredProps = [ "position" ];

mpld3_Axis.prototype.defaultProps = {
  nticks: 10,
  tickvalues: null,
  tickformat: null,
  filtered_tickvalues: null,
  filtered_tickformat: null,
  tickformat_formatter: null,
  fontsize: "11px",
  fontcolor: "black",
  axiscolor: "black",
  scale: "linear",
  grid: {},
  zorder: 0,
  visible: true
};

function mpld3_Axis(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  var trans = {
    bottom: [ 0, this.ax.height ],
    top: [ 0, 0 ],
    left: [ 0, 0 ],
    right: [ this.ax.width, 0 ]
  };
  var xy = {
    bottom: "x",
    top: "x",
    left: "y",
    right: "y"
  };
  this.ax = ax;
  this.transform = "translate(" + trans[this.props.position] + ")";
  this.props.xy = xy[this.props.position];
  this.cssclass = "mpld3-" + this.props.xy + "axis";
  this.scale = this.ax[this.props.xy + "dom"];
  this.tickNr = null;
  this.tickFormat = null;
}

mpld3_Axis.prototype.getGrid = function() {
  var gridprop = {
    nticks: this.props.nticks,
    zorder: this.props.zorder,
    tickvalues: null,
    xy: this.props.xy
  };
  if (this.props.grid) {
    for (var key in this.props.grid) {
      gridprop[key] = this.props.grid[key];
    }
  }
  return new mpld3_Grid(this.ax, gridprop);
};

mpld3_Axis.prototype.wrapTicks = function() {
  function wrap(text, width, lineHeight) {
    lineHeight = lineHeight || 1.2;
    text.each(function() {
      var text = d3.select(this);
      var bbox = text.node().getBBox();
      var textHeight = bbox.height;
      var words = text.text().split(/\s+/).reverse();
      var word;
      var line = [];
      var lineNumber = 0;
      var y = text.attr("y");
      var dy = textHeight;
      var tspan = text.text(null).append("tspan").attr("x", 0).attr("y", y).attr("dy", dy);
      while (word = words.pop()) {
        line.push(word);
        tspan.text(line.join(" "));
        if (tspan.node().getComputedTextLength() > width) {
          line.pop();
          tspan.text(line.join(" "));
          line = [ word ];
          tspan = text.append("tspan").attr("x", 0).attr("y", y).attr("dy", ++lineNumber * (textHeight * lineHeight) + dy).text(word);
        }
      }
    });
  }
  var TEXT_WIDTH = 80;
  if (this.props.xy == "x") {
    this.elem.selectAll("text").call(wrap, TEXT_WIDTH);
  }
};

mpld3_Axis.prototype.draw = function() {
  var scale = this.props.xy === "x" ? this.parent.props.xscale : this.parent.props.yscale;
  if (scale === "date" && this.props.tickvalues) {
    var domain = this.props.xy === "x" ? this.parent.x.domain() : this.parent.y.domain();
    var range = this.props.xy === "x" ? this.parent.xdom.domain() : this.parent.ydom.domain();
    var ordinal_to_js_date = d3.scaleLinear().domain(domain).range(range);
    this.props.tickvalues = this.props.tickvalues.map(function(value) {
      return new Date(ordinal_to_js_date(value));
    });
  }
  var scaleMethod = {
    left: "axisLeft",
    right: "axisRight",
    top: "axisTop",
    bottom: "axisBottom"
  }[this.props.position];
  this.axis = d3[scaleMethod](this.scale);
  var that = this;
  this.filter_ticks(this.axis.scale().domain());
  if (this.props.tickformat_formatter == "index") {
    this.axis = this.axis.tickFormat(function(d, i) {
      return that.props.filtered_tickformat[d];
    });
  } else if (this.props.tickformat_formatter == "percent") {
    this.axis = this.axis.tickFormat(function(d, i) {
      var value = d / that.props.tickformat.xmax * 100;
      var decimals = that.props.tickformat.decimals || 0;
      var formatted_string = d3.format("." + decimals + "f")(value);
      return formatted_string + that.props.tickformat.symbol;
    });
  } else if (this.props.tickformat_formatter == "str_method") {
    this.axis = this.axis.tickFormat(function(d, i) {
      var formatted_string = d3.format(that.props.tickformat.format_string)(d);
      return that.props.tickformat.prefix + formatted_string + that.props.tickformat.suffix;
    });
  } else if (this.props.tickformat_formatter == "fixed") {
    this.axis = this.axis.tickFormat(function(d, i) {
      return that.props.filtered_tickformat[i];
    });
  } else if (this.tickFormat) {
    this.axis = this.axis.tickFormat(this.tickFormat);
  }
  if (this.tickNr) {
    this.axis = this.axis.ticks(this.tickNr);
  }
  this.axis = this.axis.tickValues(this.props.filtered_tickvalues);
  this.elem = this.ax.baseaxes.append("g").attr("transform", this.transform).attr("class", this.cssclass).call(this.axis);
  this.wrapTicks();
  mpld3.insert_css("div#" + this.ax.fig.figid + " ." + this.cssclass + " line, " + " ." + this.cssclass + " path", {
    "shape-rendering": "crispEdges",
    stroke: this.props.axiscolor,
    fill: "none"
  });
  mpld3.insert_css("div#" + this.ax.fig.figid + " ." + this.cssclass + " text", {
    "font-family": "sans-serif",
    "font-size": this.props.fontsize + "px",
    fill: this.props.fontcolor,
    stroke: "none"
  });
};

mpld3_Axis.prototype.zoomed = function(transform) {
  this.filter_ticks(this.axis.scale().domain());
  this.axis = this.axis.tickValues(this.props.filtered_tickvalues);
  if (transform) {
    if (this.props.xy == "x") {
      this.elem.call(this.axis.scale(transform.rescaleX(this.scale)));
    } else {
      this.elem.call(this.axis.scale(transform.rescaleY(this.scale)));
    }
    this.wrapTicks();
  } else {
    this.elem.call(this.axis);
  }
};

mpld3_Axis.prototype.setTicks = function(nr, format) {
  this.tickNr = nr;
  this.tickFormat = format;
};

mpld3_Axis.prototype.filter_ticks = function(domain) {
  if (this.props.tickvalues) {
    const that = this;
    const filteredTickIndices = this.props.tickvalues.map(function(d, i) {
      return i;
    }).filter(function(d, i) {
      const v = that.props.tickvalues[d];
      return v >= domain[0] && v <= domain[1];
    });
    this.props.filtered_tickvalues = this.props.tickvalues.filter(function(d, i) {
      return filteredTickIndices.includes(i);
    });
    if (this.props.tickformat) {
      this.props.filtered_tickformat = this.props.tickformat.filter(function(d, i) {
        return filteredTickIndices.includes(i);
      });
    } else {
      this.props.filtered_tickformat = this.props.tickformat;
    }
  } else {
    this.props.filtered_tickvalues = this.props.tickvalues;
    this.props.filtered_tickformat = this.props.tickformat;
  }
};

mpld3.Coordinates = mpld3_Coordinates;

function mpld3_Coordinates(trans, ax) {
  this.trans = trans;
  if (typeof ax === "undefined") {
    this.ax = null;
    this.fig = null;
    if (this.trans !== "display") throw "ax must be defined if transform != 'display'";
  } else {
    this.ax = ax;
    this.fig = ax.fig;
  }
  this.zoomable = this.trans === "data";
  this.x = this["x_" + this.trans];
  this.y = this["y_" + this.trans];
  if (typeof this.x === "undefined" || typeof this.y === "undefined") throw "unrecognized coordinate code: " + this.trans;
}

mpld3_Coordinates.prototype.xy = function(d, ix, iy) {
  ix = typeof ix === "undefined" ? 0 : ix;
  iy = typeof iy === "undefined" ? 1 : iy;
  return [ this.x(d[ix]), this.y(d[iy]) ];
};

mpld3_Coordinates.prototype.x_data = function(x) {
  return this.ax.x(x);
};

mpld3_Coordinates.prototype.y_data = function(y) {
  return this.ax.y(y);
};

mpld3_Coordinates.prototype.x_display = function(x) {
  return x;
};

mpld3_Coordinates.prototype.y_display = function(y) {
  return y;
};

mpld3_Coordinates.prototype.x_axes = function(x) {
  return x * this.ax.width;
};

mpld3_Coordinates.prototype.y_axes = function(y) {
  return this.ax.height * (1 - y);
};

mpld3_Coordinates.prototype.x_figure = function(x) {
  return x * this.fig.width - this.ax.position[0];
};

mpld3_Coordinates.prototype.y_figure = function(y) {
  return (1 - y) * this.fig.height - this.ax.position[1];
};

mpld3.Path = mpld3_Path;

mpld3_Path.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Path.prototype.constructor = mpld3_Path;

mpld3_Path.prototype.requiredProps = [ "data" ];

mpld3_Path.prototype.defaultProps = {
  xindex: 0,
  yindex: 1,
  coordinates: "data",
  facecolor: "green",
  edgecolor: "black",
  edgewidth: 1,
  dasharray: "none",
  pathcodes: null,
  offset: null,
  offsetcoordinates: "data",
  alpha: 1,
  drawstyle: "none",
  zorder: 1
};

function mpld3_Path(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  this.data = ax.fig.get_data(this.props.data);
  this.pathcodes = this.props.pathcodes;
  this.pathcoords = new mpld3_Coordinates(this.props.coordinates, this.ax);
  this.offsetcoords = new mpld3_Coordinates(this.props.offsetcoordinates, this.ax);
  this.datafunc = mpld3_path();
}

mpld3_Path.prototype.finiteFilter = function(d, i) {
  return isFinite(this.pathcoords.x(d[this.props.xindex])) && isFinite(this.pathcoords.y(d[this.props.yindex]));
};

mpld3_Path.prototype.draw = function() {
  this.datafunc.defined(this.finiteFilter.bind(this)).x(function(d) {
    return this.pathcoords.x(d[this.props.xindex]);
  }.bind(this)).y(function(d) {
    return this.pathcoords.y(d[this.props.yindex]);
  }.bind(this));
  if (this.pathcoords.zoomable) {
    this.path = this.ax.paths.append("svg:path");
  } else {
    this.path = this.ax.staticPaths.append("svg:path");
  }
  this.path = this.path.attr("d", this.datafunc(this.data, this.pathcodes)).attr("class", "mpld3-path").style("stroke", this.props.edgecolor).style("stroke-width", this.props.edgewidth).style("stroke-dasharray", this.props.dasharray).style("stroke-opacity", this.props.alpha).style("fill", this.props.facecolor).style("fill-opacity", this.props.alpha).attr("vector-effect", "non-scaling-stroke");
  if (this.props.offset !== null) {
    var offset = this.offsetcoords.xy(this.props.offset);
    this.path.attr("transform", "translate(" + offset + ")");
  }
};

mpld3_Path.prototype.elements = function(d) {
  return this.path;
};

mpld3.PathCollection = mpld3_PathCollection;

mpld3_PathCollection.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_PathCollection.prototype.constructor = mpld3_PathCollection;

mpld3_PathCollection.prototype.requiredProps = [ "paths", "offsets" ];

mpld3_PathCollection.prototype.defaultProps = {
  xindex: 0,
  yindex: 1,
  pathtransforms: [],
  pathcoordinates: "display",
  offsetcoordinates: "data",
  offsetorder: "before",
  edgecolors: [ "#000000" ],
  drawstyle: "none",
  edgewidths: [ 1 ],
  facecolors: [ "#0000FF" ],
  alphas: [ 1 ],
  zorder: 2
};

function mpld3_PathCollection(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  if (this.props.facecolors == null || this.props.facecolors.length == 0) {
    this.props.facecolors = [ "none" ];
  }
  if (this.props.edgecolors == null || this.props.edgecolors.length == 0) {
    this.props.edgecolors = [ "none" ];
  }
  var offsets = this.ax.fig.get_data(this.props.offsets);
  if (offsets === null || offsets.length === 0) offsets = [ null ];
  var N = Math.max(this.props.paths.length, offsets.length);
  if (offsets.length === N) {
    this.offsets = offsets;
  } else {
    this.offsets = [];
    for (var i = 0; i < N; i++) this.offsets.push(getMod(offsets, i));
  }
  this.pathcoords = new mpld3_Coordinates(this.props.pathcoordinates, this.ax);
  this.offsetcoords = new mpld3_Coordinates(this.props.offsetcoordinates, this.ax);
}

mpld3_PathCollection.prototype.transformFunc = function(d, i) {
  var t = this.props.pathtransforms;
  var transform = t.length == 0 ? "" : mpld3.getTransformation("matrix(" + getMod(t, i) + ")").toString();
  var offset = d === null || typeof d === "undefined" ? "translate(0, 0)" : "translate(" + this.offsetcoords.xy(d, this.props.xindex, this.props.yindex) + ")";
  return this.props.offsetorder === "after" ? transform + offset : offset + transform;
};

mpld3_PathCollection.prototype.pathFunc = function(d, i) {
  return mpld3_path().x(function(d) {
    return this.pathcoords.x(d[0]);
  }.bind(this)).y(function(d) {
    return this.pathcoords.y(d[1]);
  }.bind(this)).apply(this, getMod(this.props.paths, i));
};

mpld3_PathCollection.prototype.styleFunc = function(d, i) {
  var styles = {
    stroke: getMod(this.props.edgecolors, i),
    "stroke-width": getMod(this.props.edgewidths, i),
    "stroke-opacity": getMod(this.props.alphas, i),
    fill: getMod(this.props.facecolors, i),
    "fill-opacity": getMod(this.props.alphas, i)
  };
  var ret = "";
  for (var key in styles) {
    ret += key + ":" + styles[key] + ";";
  }
  return ret;
};

mpld3_PathCollection.prototype.allFinite = function(d) {
  if (d instanceof Array) {
    return d.length == d.filter(isFinite).length;
  } else {
    return true;
  }
};

mpld3_PathCollection.prototype.draw = function() {
  if (this.offsetcoords.zoomable || this.pathcoords.zoomable) {
    this.group = this.ax.paths.append("svg:g");
  } else {
    this.group = this.ax.staticPaths.append("svg:g");
  }
  this.pathsobj = this.group.selectAll("paths").data(this.offsets.filter(this.allFinite)).enter().append("svg:path").attr("d", this.pathFunc.bind(this)).attr("class", "mpld3-path").attr("transform", this.transformFunc.bind(this)).attr("style", this.styleFunc.bind(this)).attr("vector-effect", "non-scaling-stroke");
};

mpld3_PathCollection.prototype.elements = function(d) {
  return this.group.selectAll("path");
};

mpld3.Line = mpld3_Line;

mpld3_Line.prototype = Object.create(mpld3_Path.prototype);

mpld3_Line.prototype.constructor = mpld3_Line;

mpld3_Line.prototype.requiredProps = [ "data" ];

mpld3_Line.prototype.defaultProps = {
  xindex: 0,
  yindex: 1,
  coordinates: "data",
  color: "salmon",
  linewidth: 2,
  dasharray: "none",
  alpha: 1,
  zorder: 2,
  drawstyle: "none"
};

function mpld3_Line(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  var pathProps = this.props;
  pathProps.facecolor = "none";
  pathProps.edgecolor = pathProps.color;
  delete pathProps.color;
  pathProps.edgewidth = pathProps.linewidth;
  delete pathProps.linewidth;
  const drawstyle = pathProps.drawstyle;
  delete pathProps.drawstyle;
  this.defaultProps = mpld3_Path.prototype.defaultProps;
  mpld3_Path.call(this, ax, pathProps);
  switch (drawstyle) {
   case "steps":
   case "steps-pre":
    this.datafunc = d3.line().curve(d3.curveStepBefore);
    break;

   case "steps-post":
    this.datafunc = d3.line().curve(d3.curveStepAfter);
    break;

   case "steps-mid":
    this.datafunc = d3.line().curve(d3.curveStep);
    break;

   default:
    this.datafunc = d3.line().curve(d3.curveLinear);
  }
}

mpld3.Markers = mpld3_Markers;

mpld3_Markers.prototype = Object.create(mpld3_PathCollection.prototype);

mpld3_Markers.prototype.constructor = mpld3_Markers;

mpld3_Markers.prototype.requiredProps = [ "data" ];

mpld3_Markers.prototype.defaultProps = {
  xindex: 0,
  yindex: 1,
  coordinates: "data",
  facecolor: "salmon",
  edgecolor: "black",
  edgewidth: 1,
  alpha: 1,
  markersize: 6,
  markername: "circle",
  drawstyle: "none",
  markerpath: null,
  zorder: 3
};

function mpld3_Markers(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  if (this.props.markerpath !== null) {
    this.marker = this.props.markerpath[0].length == 0 ? null : mpld3.path().call(this.props.markerpath[0], this.props.markerpath[1]);
  } else {
    this.marker = this.props.markername === null ? null : d3.symbol(this.props.markername).size(Math.pow(this.props.markersize, 2))();
  }
  var PCprops = {
    paths: [ this.props.markerpath ],
    offsets: ax.fig.parse_offsets(ax.fig.get_data(this.props.data, true)),
    xindex: this.props.xindex,
    yindex: this.props.yindex,
    offsetcoordinates: this.props.coordinates,
    edgecolors: [ this.props.edgecolor ],
    edgewidths: [ this.props.edgewidth ],
    facecolors: [ this.props.facecolor ],
    alphas: [ this.props.alpha ],
    zorder: this.props.zorder,
    id: this.props.id
  };
  this.requiredProps = mpld3_PathCollection.prototype.requiredProps;
  this.defaultProps = mpld3_PathCollection.prototype.defaultProps;
  mpld3_PathCollection.call(this, ax, PCprops);
}

mpld3_Markers.prototype.pathFunc = function(d, i) {
  return this.marker;
};

mpld3.Image = mpld3_Image;

mpld3_Image.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Image.prototype.constructor = mpld3_Image;

mpld3_Image.prototype.requiredProps = [ "data", "extent" ];

mpld3_Image.prototype.defaultProps = {
  alpha: 1,
  coordinates: "data",
  drawstyle: "none",
  zorder: 1
};

function mpld3_Image(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  this.coords = new mpld3_Coordinates(this.props.coordinates, this.ax);
}

mpld3_Image.prototype.draw = function() {
  this.image = this.ax.paths.append("svg:image");
  this.image = this.image.attr("class", "mpld3-image").attr("xlink:href", "data:image/png;base64," + this.props.data).style("opacity", this.props.alpha).attr("preserveAspectRatio", "none");
  this.updateDimensions();
};

mpld3_Image.prototype.elements = function(d) {
  return d3.select(this.image);
};

mpld3_Image.prototype.updateDimensions = function() {
  var extent = this.props.extent;
  this.image.attr("x", this.coords.x(extent[0])).attr("y", this.coords.y(extent[3])).attr("width", this.coords.x(extent[1]) - this.coords.x(extent[0])).attr("height", this.coords.y(extent[2]) - this.coords.y(extent[3]));
};

mpld3.Text = mpld3_Text;

mpld3_Text.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Text.prototype.constructor = mpld3_Text;

mpld3_Text.prototype.requiredProps = [ "text", "position" ];

mpld3_Text.prototype.defaultProps = {
  coordinates: "data",
  h_anchor: "start",
  v_baseline: "auto",
  rotation: 0,
  fontsize: 11,
  drawstyle: "none",
  color: "black",
  alpha: 1,
  zorder: 3
};

function mpld3_Text(ax, props) {
  mpld3_PlotElement.call(this, ax, props);
  this.text = this.props.text;
  this.position = this.props.position;
  this.coords = new mpld3_Coordinates(this.props.coordinates, this.ax);
}

mpld3_Text.prototype.draw = function() {
  if (this.props.coordinates == "data") {
    if (this.coords.zoomable) {
      this.obj = this.ax.paths.append("text");
    } else {
      this.obj = this.ax.staticPaths.append("text");
    }
  } else {
    this.obj = this.ax.baseaxes.append("text");
  }
  this.obj.attr("class", "mpld3-text").text(this.text).style("text-anchor", this.props.h_anchor).style("dominant-baseline", this.props.v_baseline).style("font-size", this.props.fontsize).style("fill", this.props.color).style("opacity", this.props.alpha);
  this.applyTransform();
};

mpld3_Text.prototype.elements = function(d) {
  return d3.select(this.obj);
};

mpld3_Text.prototype.applyTransform = function() {
  var pos = this.coords.xy(this.position);
  this.obj.attr("x", pos[0]).attr("y", pos[1]);
  if (this.props.rotation) this.obj.attr("transform", "rotate(" + this.props.rotation + "," + pos + ")");
};

mpld3.Axes = mpld3_Axes;

mpld3_Axes.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Axes.prototype.constructor = mpld3_Axes;

mpld3_Axes.prototype.requiredProps = [ "xlim", "ylim" ];

mpld3_Axes.prototype.defaultProps = {
  bbox: [ .1, .1, .8, .8 ],
  axesbg: "#FFFFFF",
  axesbgalpha: 1,
  gridOn: false,
  xdomain: null,
  ydomain: null,
  xscale: "linear",
  yscale: "linear",
  zoomable: true,
  axes: [ {
    position: "left"
  }, {
    position: "bottom"
  } ],
  lines: [],
  paths: [],
  markers: [],
  texts: [],
  collections: [],
  sharex: [],
  sharey: [],
  images: []
};

function mpld3_Axes(fig, props) {
  mpld3_PlotElement.call(this, fig, props);
  this.axnum = this.fig.axes.length;
  this.axid = this.fig.figid + "_ax" + (this.axnum + 1);
  this.clipid = this.axid + "_clip";
  this.props.xdomain = this.props.xdomain || this.props.xlim;
  this.props.ydomain = this.props.ydomain || this.props.ylim;
  this.sharex = [];
  this.sharey = [];
  this.elements = [];
  this.axisList = [];
  var bbox = this.props.bbox;
  this.position = [ bbox[0] * this.fig.width, (1 - bbox[1] - bbox[3]) * this.fig.height ];
  this.width = bbox[2] * this.fig.width;
  this.height = bbox[3] * this.fig.height;
  this.isZoomEnabled = null;
  this.zoom = null;
  this.lastTransform = d3.zoomIdentity;
  this.isBoxzoomEnabled = null;
  this.isLinkedBrushEnabled = null;
  this.isCurrentLinkedBrushTarget = false;
  this.brushG = null;
  function buildDate(d) {
    return new Date(d[0], d[1], d[2], d[3], d[4], d[5]);
  }
  function setDomain(scale, domain) {
    return scale !== "date" ? domain : [ buildDate(domain[0]), buildDate(domain[1]) ];
  }
  this.props.xdomain = setDomain(this.props.xscale, this.props.xdomain);
  this.props.ydomain = setDomain(this.props.yscale, this.props.ydomain);
  function build_scale(scale, domain, range) {
    var dom = scale === "date" ? d3.scaleTime() : scale === "log" ? d3.scaleLog() : d3.scaleLinear();
    return dom.domain(domain).range(range);
  }
  this.x = this.xdom = build_scale(this.props.xscale, this.props.xdomain, [ 0, this.width ]);
  this.y = this.ydom = build_scale(this.props.yscale, this.props.ydomain, [ this.height, 0 ]);
  if (this.props.xscale === "date") {
    this.x = mpld3.multiscale(d3.scaleLinear().domain(this.props.xlim).range(this.props.xdomain.map(Number)), this.xdom);
  }
  if (this.props.yscale === "date") {
    this.y = mpld3.multiscale(d3.scaleLinear().domain(this.props.ylim).range(this.props.ydomain.map(Number)), this.ydom);
  }
  var axes = this.props.axes;
  for (var i = 0; i < axes.length; i++) {
    var axis = new mpld3.Axis(this, axes[i]);
    this.axisList.push(axis);
    this.elements.push(axis);
    if (this.props.gridOn || axis.props.grid.gridOn) {
      this.elements.push(axis.getGrid());
    }
  }
  var paths = this.props.paths;
  for (var i = 0; i < paths.length; i++) {
    this.elements.push(new mpld3.Path(this, paths[i]));
  }
  var lines = this.props.lines;
  for (var i = 0; i < lines.length; i++) {
    this.elements.push(new mpld3.Line(this, lines[i]));
  }
  var markers = this.props.markers;
  for (var i = 0; i < markers.length; i++) {
    this.elements.push(new mpld3.Markers(this, markers[i]));
  }
  var texts = this.props.texts;
  for (var i = 0; i < texts.length; i++) {
    this.elements.push(new mpld3.Text(this, texts[i]));
  }
  var collections = this.props.collections;
  for (var i = 0; i < collections.length; i++) {
    this.elements.push(new mpld3.PathCollection(this, collections[i]));
  }
  var images = this.props.images;
  for (var i = 0; i < images.length; i++) {
    this.elements.push(new mpld3.Image(this, images[i]));
  }
  this.elements.sort(function(a, b) {
    return a.props.zorder - b.props.zorder;
  });
}

mpld3_Axes.prototype.draw = function() {
  for (var i = 0; i < this.props.sharex.length; i++) {
    this.sharex.push(mpld3.get_element(this.props.sharex[i]));
  }
  for (var i = 0; i < this.props.sharey.length; i++) {
    this.sharey.push(mpld3.get_element(this.props.sharey[i]));
  }
  this.baseaxes = this.fig.canvas.append("g").attr("transform", "translate(" + this.position[0] + "," + this.position[1] + ")").attr("width", this.width).attr("height", this.height).attr("class", "mpld3-baseaxes");
  this.axes = this.baseaxes.append("g").attr("class", "mpld3-axes").style("pointer-events", "visiblefill");
  this.clip = this.axes.append("svg:clipPath").attr("id", this.clipid).append("svg:rect").attr("x", 0).attr("y", 0).attr("width", this.width).attr("height", this.height);
  this.axesbg = this.axes.append("svg:rect").attr("width", this.width).attr("height", this.height).attr("class", "mpld3-axesbg").style("fill", this.props.axesbg).style("fill-opacity", this.props.axesbgalpha);
  this.pathsContainer = this.axes.append("g").attr("clip-path", "url(#" + this.clipid + ")").attr("x", 0).attr("y", 0).attr("width", this.width).attr("height", this.height).attr("class", "mpld3-paths-container");
  this.paths = this.pathsContainer.append("g").attr("class", "mpld3-paths");
  this.staticPaths = this.axes.append("g").attr("class", "mpld3-staticpaths");
  this.brush = d3.brush().extent([ [ 0, 0 ], [ this.fig.width, this.fig.height ] ]).on("start", this.brushStart.bind(this)).on("brush", this.brushMove.bind(this)).on("end", this.brushEnd.bind(this)).on("start.nokey", function() {
    d3.select(window).on("keydown.brush keyup.brush", null);
  });
  for (var i = 0; i < this.elements.length; i++) {
    this.elements[i].draw();
  }
};

mpld3_Axes.prototype.bindZoom = function() {
  if (!this.zoom) {
    this.zoom = d3.zoom();
    this.zoom.on("zoom", this.zoomed.bind(this));
    this.axes.call(this.zoom);
  }
};

mpld3_Axes.prototype.unbindZoom = function() {
  if (this.zoom) {
    this.zoom.on("zoom", null);
    this.axes.on(".zoom", null);
    this.zoom = null;
  }
};

mpld3_Axes.prototype.bindBrush = function() {
  if (!this.brushG) {
    this.brushG = this.axes.append("g").attr("class", "mpld3-brush").call(this.brush);
  }
};

mpld3_Axes.prototype.unbindBrush = function() {
  if (this.brushG) {
    this.brushG.remove();
    this.brushG.on(".brush", null);
    this.brushG = null;
  }
};

mpld3_Axes.prototype.reset = function() {
  if (this.zoom) {
    this.doZoom(false, d3.zoomIdentity, 750);
  } else {
    this.bindZoom();
    this.doZoom(false, d3.zoomIdentity, 750, function() {
      if (this.isSomeTypeOfZoomEnabled) {
        return;
      }
      this.unbindZoom();
    }.bind(this));
  }
};

mpld3_Axes.prototype.enableOrDisableBrushing = function() {
  if (this.isBoxzoomEnabled || this.isLinkedBrushEnabled) {
    this.bindBrush();
  } else {
    this.unbindBrush();
  }
};

mpld3_Axes.prototype.isSomeTypeOfZoomEnabled = function() {
  return this.isZoomEnabled || this.isBoxzoomEnabled;
};

mpld3_Axes.prototype.enableOrDisableZooming = function() {
  if (this.isSomeTypeOfZoomEnabled()) {
    this.bindZoom();
  } else {
    this.unbindZoom();
  }
};

mpld3_Axes.prototype.enableLinkedBrush = function() {
  this.isLinkedBrushEnabled = true;
  this.enableOrDisableBrushing();
};

mpld3_Axes.prototype.disableLinkedBrush = function() {
  this.isLinkedBrushEnabled = false;
  this.enableOrDisableBrushing();
};

mpld3_Axes.prototype.enableBoxzoom = function() {
  this.isBoxzoomEnabled = true;
  this.enableOrDisableBrushing();
  this.enableOrDisableZooming();
};

mpld3_Axes.prototype.disableBoxzoom = function() {
  this.isBoxzoomEnabled = false;
  this.enableOrDisableBrushing();
  this.enableOrDisableZooming();
};

mpld3_Axes.prototype.enableZoom = function() {
  this.isZoomEnabled = true;
  this.enableOrDisableZooming();
  this.axes.style("cursor", "move");
};

mpld3_Axes.prototype.disableZoom = function() {
  this.isZoomEnabled = false;
  this.enableOrDisableZooming();
  this.axes.style("cursor", null);
};

mpld3_Axes.prototype.doZoom = function(propagate, transform, duration, onTransitionEnd) {
  if (!this.props.zoomable || !this.zoom) {
    return;
  }
  if (duration) {
    var transition = this.axes.transition().duration(duration).call(this.zoom.transform, transform);
    if (onTransitionEnd) {
      transition.on("end", onTransitionEnd);
    }
  } else {
    this.axes.call(this.zoom.transform, transform);
  }
  if (propagate) {
    this.lastTransform = transform;
    this.sharex.forEach(function(sharedAxes) {
      sharedAxes.doZoom(false, transform, duration);
    });
    this.sharey.forEach(function(sharedAxes) {
      sharedAxes.doZoom(false, transform, duration);
    });
  } else {
    this.lastTransform = transform;
  }
};

mpld3_Axes.prototype.zoomed = function() {
  var isProgrammatic = d3.event.sourceEvent && d3.event.sourceEvent.type != "zoom";
  if (isProgrammatic) {
    this.doZoom(true, d3.event.transform, false);
  } else {
    var transform = d3.event.transform;
    this.paths.attr("transform", transform);
    this.elements.forEach(function(element) {
      if (element.zoomed) {
        element.zoomed(transform);
      }
    }.bind(this));
  }
};

mpld3_Axes.prototype.resetBrush = function() {
  this.brushG.call(this.brush.move, null);
};

mpld3_Axes.prototype.doBoxzoom = function(selection) {
  if (!selection || !this.brushG) {
    return;
  }
  var sel = selection.map(this.lastTransform.invert, this.lastTransform);
  var dx = sel[1][0] - sel[0][0];
  var dy = sel[1][1] - sel[0][1];
  var cx = (sel[0][0] + sel[1][0]) / 2;
  var cy = (sel[0][1] + sel[1][1]) / 2;
  var scale = dx > dy ? this.width / dx : this.height / dy;
  var transX = this.width / 2 - scale * cx;
  var transY = this.height / 2 - scale * cy;
  var transform = d3.zoomIdentity.translate(transX, transY).scale(scale);
  this.doZoom(true, transform, 750);
  this.resetBrush();
};

mpld3_Axes.prototype.brushStart = function() {
  if (this.isLinkedBrushEnabled) {
    this.isCurrentLinkedBrushTarget = d3.event.sourceEvent.constructor.name == "MouseEvent";
    if (this.isCurrentLinkedBrushTarget) {
      this.fig.resetBrushForOtherAxes(this.axid);
    }
  }
};

mpld3_Axes.prototype.brushMove = function() {
  var selection = d3.event.selection;
  if (this.isLinkedBrushEnabled) {
    this.fig.updateLinkedBrush(selection);
  }
};

mpld3_Axes.prototype.brushEnd = function() {
  var selection = d3.event.selection;
  if (this.isBoxzoomEnabled) {
    this.doBoxzoom(selection);
  }
  if (this.isLinkedBrushEnabled) {
    if (!selection) {
      this.fig.endLinkedBrush();
    }
    this.isCurrentLinkedBrushTarget = false;
  }
};

mpld3_Axes.prototype.setTicks = function(xy, nr, format) {
  this.axisList.forEach(function(axis) {
    if (axis.props.xy == xy) {
      axis.setTicks(nr, format);
    }
  });
};

mpld3.Toolbar = mpld3_Toolbar;

mpld3_Toolbar.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Toolbar.prototype.constructor = mpld3_Toolbar;

mpld3_Toolbar.prototype.defaultProps = {
  buttons: [ "reset", "move" ]
};

function mpld3_Toolbar(fig, props) {
  mpld3_PlotElement.call(this, fig, props);
  this.buttons = [];
  this.props.buttons.forEach(this.addButton.bind(this));
}

mpld3_Toolbar.prototype.addButton = function(button) {
  this.buttons.push(new button(this));
};

mpld3_Toolbar.prototype.draw = function() {
  mpld3.insert_css("div#" + this.fig.figid + " .mpld3-toolbar image", {
    cursor: "pointer",
    opacity: .2,
    display: "inline-block",
    margin: "0px"
  });
  mpld3.insert_css("div#" + this.fig.figid + " .mpld3-toolbar image.active", {
    opacity: .4
  });
  mpld3.insert_css("div#" + this.fig.figid + " .mpld3-toolbar image.pressed", {
    opacity: .6
  });
  function showButtons() {
    this.buttonsobj.transition(750).attr("y", 0);
  }
  function hideButtons() {
    this.buttonsobj.transition(750).delay(250).attr("y", 16);
  }
  this.fig.canvas.on("mouseenter", showButtons.bind(this)).on("mouseleave", hideButtons.bind(this)).on("touchenter", showButtons.bind(this)).on("touchstart", showButtons.bind(this));
  this.toolbar = this.fig.canvas.append("svg:svg").attr("width", 16 * this.buttons.length).attr("height", 16).attr("x", 2).attr("y", this.fig.height - 16 - 2).attr("class", "mpld3-toolbar");
  this.buttonsobj = this.toolbar.append("svg:g").selectAll("buttons").data(this.buttons).enter().append("svg:image").attr("class", function(d) {
    return d.cssclass;
  }).attr("xlink:href", function(d) {
    return d.icon();
  }).attr("width", 16).attr("height", 16).attr("x", function(d, i) {
    return i * 16;
  }).attr("y", 16).on("click", function(d) {
    d.click();
  }).on("mouseenter", function() {
    d3.select(this).classed("active", true);
  }).on("mouseleave", function() {
    d3.select(this).classed("active", false);
  });
  for (var i = 0; i < this.buttons.length; i++) this.buttons[i].onDraw();
};

mpld3_Toolbar.prototype.deactivate_all = function() {
  this.buttons.forEach(function(b) {
    b.deactivate();
  });
};

mpld3_Toolbar.prototype.deactivate_by_action = function(actions) {
  function filt(e) {
    return actions.indexOf(e) !== -1;
  }
  if (actions.length > 0) {
    this.buttons.forEach(function(button) {
      if (button.actions.filter(filt).length > 0) button.deactivate();
    });
  }
};

mpld3.Button = mpld3_Button;

mpld3_Button.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Button.prototype.constructor = mpld3_Button;

function mpld3_Button(toolbar, key) {
  mpld3_PlotElement.call(this, toolbar);
  this.toolbar = toolbar;
  this.fig = this.toolbar.fig;
  this.cssclass = "mpld3-" + key + "button";
  this.active = false;
}

mpld3_Button.prototype.setState = function(state) {
  state ? this.activate() : this.deactivate();
};

mpld3_Button.prototype.click = function() {
  this.active ? this.deactivate() : this.activate();
};

mpld3_Button.prototype.activate = function() {
  this.toolbar.deactivate_by_action(this.actions);
  this.onActivate();
  this.active = true;
  this.toolbar.toolbar.select("." + this.cssclass).classed("pressed", true);
  if (!this.sticky) {
    this.deactivate();
  }
};

mpld3_Button.prototype.deactivate = function() {
  this.onDeactivate();
  this.active = false;
  this.toolbar.toolbar.select("." + this.cssclass).classed("pressed", false);
};

mpld3_Button.prototype.sticky = false;

mpld3_Button.prototype.actions = [];

mpld3_Button.prototype.icon = function() {
  return "";
};

mpld3_Button.prototype.onActivate = function() {};

mpld3_Button.prototype.onDeactivate = function() {};

mpld3_Button.prototype.onDraw = function() {};

mpld3.ButtonFactory = function(members) {
  if (typeof members.buttonID !== "string") {
    throw "ButtonFactory: buttonID must be present and be a string";
  }
  function B(toolbar) {
    mpld3_Button.call(this, toolbar, this.buttonID);
  }
  B.prototype = Object.create(mpld3_Button.prototype);
  B.prototype.constructor = B;
  for (var key in members) {
    B.prototype[key] = members[key];
  }
  return B;
};

mpld3.Plugin = mpld3_Plugin;

mpld3_Plugin.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Plugin.prototype.constructor = mpld3_Plugin;

mpld3_Plugin.prototype.requiredProps = [];

mpld3_Plugin.prototype.defaultProps = {};

function mpld3_Plugin(fig, props) {
  mpld3_PlotElement.call(this, fig, props);
}

mpld3_Plugin.prototype.draw = function() {};

mpld3.ResetPlugin = mpld3_ResetPlugin;

mpld3.register_plugin("reset", mpld3_ResetPlugin);

mpld3_ResetPlugin.prototype = Object.create(mpld3_Plugin.prototype);

mpld3_ResetPlugin.prototype.constructor = mpld3_ResetPlugin;

mpld3_ResetPlugin.prototype.requiredProps = [];

mpld3_ResetPlugin.prototype.defaultProps = {};

function mpld3_ResetPlugin(fig, props) {
  mpld3_Plugin.call(this, fig, props);
  var ResetButton = mpld3.ButtonFactory({
    buttonID: "reset",
    sticky: false,
    onActivate: function() {
      this.toolbar.fig.reset();
    },
    icon: function() {
      return mpld3.icons["reset"];
    }
  });
  this.fig.buttons.push(ResetButton);
}

mpld3.ZoomPlugin = mpld3_ZoomPlugin;

mpld3.register_plugin("zoom", mpld3_ZoomPlugin);

mpld3_ZoomPlugin.prototype = Object.create(mpld3_Plugin.prototype);

mpld3_ZoomPlugin.prototype.constructor = mpld3_ZoomPlugin;

mpld3_ZoomPlugin.prototype.requiredProps = [];

mpld3_ZoomPlugin.prototype.defaultProps = {
  button: true,
  enabled: null
};

function mpld3_ZoomPlugin(fig, props) {
  mpld3_Plugin.call(this, fig, props);
  if (this.props.enabled === null) {
    this.props.enabled = !this.props.button;
  }
  var enabled = this.props.enabled;
  if (this.props.button) {
    var ZoomButton = mpld3.ButtonFactory({
      buttonID: "zoom",
      sticky: true,
      actions: [ "scroll", "drag" ],
      onActivate: this.activate.bind(this),
      onDeactivate: this.deactivate.bind(this),
      onDraw: function() {
        this.setState(enabled);
      },
      icon: function() {
        return mpld3.icons["move"];
      }
    });
    this.fig.buttons.push(ZoomButton);
  }
}

mpld3_ZoomPlugin.prototype.activate = function() {
  this.fig.enableZoom();
};

mpld3_ZoomPlugin.prototype.deactivate = function() {
  this.fig.disableZoom();
};

mpld3_ZoomPlugin.prototype.draw = function() {
  if (this.props.enabled) {
    this.activate();
  } else {
    this.deactivate();
  }
};

mpld3.BoxZoomPlugin = mpld3_BoxZoomPlugin;

mpld3.register_plugin("boxzoom", mpld3_BoxZoomPlugin);

mpld3_BoxZoomPlugin.prototype = Object.create(mpld3_Plugin.prototype);

mpld3_BoxZoomPlugin.prototype.constructor = mpld3_BoxZoomPlugin;

mpld3_BoxZoomPlugin.prototype.requiredProps = [];

mpld3_BoxZoomPlugin.prototype.defaultProps = {
  button: true,
  enabled: null
};

function mpld3_BoxZoomPlugin(fig, props) {
  mpld3_Plugin.call(this, fig, props);
  if (this.props.enabled === null) {
    this.props.enabled = !this.props.button;
  }
  var enabled = this.props.enabled;
  if (this.props.button) {
    var BoxZoomButton = mpld3.ButtonFactory({
      buttonID: "boxzoom",
      sticky: true,
      actions: [ "drag" ],
      onActivate: this.activate.bind(this),
      onDeactivate: this.deactivate.bind(this),
      onDraw: function() {
        this.setState(enabled);
      },
      icon: function() {
        return mpld3.icons["zoom"];
      }
    });
    this.fig.buttons.push(BoxZoomButton);
  }
  this.extentClass = "boxzoombrush";
}

mpld3_BoxZoomPlugin.prototype.activate = function() {
  this.fig.enableBoxzoom();
};

mpld3_BoxZoomPlugin.prototype.deactivate = function() {
  this.fig.disableBoxzoom();
};

mpld3_BoxZoomPlugin.prototype.draw = function() {
  if (this.props.enabled) {
    this.activate();
  } else {
    this.deactivate();
  }
};

mpld3.TooltipPlugin = mpld3_TooltipPlugin;

mpld3.register_plugin("tooltip", mpld3_TooltipPlugin);

mpld3_TooltipPlugin.prototype = Object.create(mpld3_Plugin.prototype);

mpld3_TooltipPlugin.prototype.constructor = mpld3_TooltipPlugin;

mpld3_TooltipPlugin.prototype.requiredProps = [ "id" ];

mpld3_TooltipPlugin.prototype.defaultProps = {
  labels: null,
  hoffset: 0,
  voffset: 10,
  location: "mouse"
};

function mpld3_TooltipPlugin(fig, props) {
  mpld3_Plugin.call(this, fig, props);
}

mpld3_TooltipPlugin.prototype.draw = function() {
  var obj = mpld3.get_element(this.props.id, this.fig);
  var labels = this.props.labels;
  var loc = this.props.location;
  this.tooltip = this.fig.canvas.append("text").attr("class", "mpld3-tooltip-text").attr("x", 0).attr("y", 0).text("").style("visibility", "hidden");
  if (loc == "bottom left" || loc == "top left") {
    this.x = obj.ax.position[0] + 5 + this.props.hoffset;
    this.tooltip.style("text-anchor", "beginning");
  } else if (loc == "bottom right" || loc == "top right") {
    this.x = obj.ax.position[0] + obj.ax.width - 5 + this.props.hoffset;
    this.tooltip.style("text-anchor", "end");
  } else {
    this.tooltip.style("text-anchor", "middle");
  }
  if (loc == "bottom left" || loc == "bottom right") {
    this.y = obj.ax.position[1] + obj.ax.height - 5 + this.props.voffset;
  } else if (loc == "top left" || loc == "top right") {
    this.y = obj.ax.position[1] + 5 + this.props.voffset;
  }
  function mouseover(d, i) {
    this.tooltip.style("visibility", "visible").text(labels === null ? "(" + d + ")" : getMod(labels, i));
  }
  function mousemove(d, i) {
    if (loc === "mouse") {
      var pos = d3.mouse(this.fig.canvas.node());
      this.x = pos[0] + this.props.hoffset;
      this.y = pos[1] - this.props.voffset;
    }
    this.tooltip.attr("x", this.x).attr("y", this.y);
  }
  function mouseout(d, i) {
    this.tooltip.style("visibility", "hidden");
  }
  obj.elements().on("mouseover", mouseover.bind(this)).on("mousemove", mousemove.bind(this)).on("mouseout", mouseout.bind(this));
};

mpld3.LinkedBrushPlugin = mpld3_LinkedBrushPlugin;

mpld3.register_plugin("linkedbrush", mpld3_LinkedBrushPlugin);

mpld3_LinkedBrushPlugin.prototype = Object.create(mpld3.Plugin.prototype);

mpld3_LinkedBrushPlugin.prototype.constructor = mpld3_LinkedBrushPlugin;

mpld3_LinkedBrushPlugin.prototype.requiredProps = [ "id" ];

mpld3_LinkedBrushPlugin.prototype.defaultProps = {
  button: true,
  enabled: null
};

function mpld3_LinkedBrushPlugin(fig, props) {
  mpld3.Plugin.call(this, fig, props);
  if (this.props.enabled === null) {
    this.props.enabled = !this.props.button;
  }
  var enabled = this.props.enabled;
  if (this.props.button) {
    var BrushButton = mpld3.ButtonFactory({
      buttonID: "linkedbrush",
      sticky: true,
      actions: [ "drag" ],
      onActivate: this.activate.bind(this),
      onDeactivate: this.deactivate.bind(this),
      onDraw: function() {
        this.setState(enabled);
      },
      icon: function() {
        return mpld3.icons["brush"];
      }
    });
    this.fig.buttons.push(BrushButton);
  }
  this.pathCollectionsByAxes = [];
  this.objectsByAxes = [];
  this.allObjects = [];
  this.extentClass = "linkedbrush";
  this.dataKey = "offsets";
  this.objectClass = null;
}

mpld3_LinkedBrushPlugin.prototype.activate = function() {
  this.fig.enableLinkedBrush();
};

mpld3_LinkedBrushPlugin.prototype.deactivate = function() {
  this.fig.disableLinkedBrush();
};

mpld3_LinkedBrushPlugin.prototype.isPathInSelection = function(path, ix, iy, sel) {
  var result = sel[0][0] < path[ix] && sel[1][0] > path[ix] && sel[0][1] < path[iy] && sel[1][1] > path[iy];
  return result;
};

mpld3_LinkedBrushPlugin.prototype.invertSelection = function(sel, axes) {
  var xs = [ axes.x.invert(sel[0][0]), axes.x.invert(sel[1][0]) ];
  var ys = [ axes.y.invert(sel[1][1]), axes.y.invert(sel[0][1]) ];
  return [ [ Math.min.apply(Math, xs), Math.min.apply(Math, ys) ], [ Math.max.apply(Math, xs), Math.max.apply(Math, ys) ] ];
};

mpld3_LinkedBrushPlugin.prototype.update = function(selection) {
  if (!selection) {
    return;
  }
  this.pathCollectionsByAxes.forEach(function(axesColls, axesIndex) {
    var pathCollection = axesColls[0];
    var objects = this.objectsByAxes[axesIndex];
    var invertedSelection = this.invertSelection(selection, this.fig.axes[axesIndex]);
    var ix = pathCollection.props.xindex;
    var iy = pathCollection.props.yindex;
    objects.selectAll("path").classed("mpld3-hidden", function(path, idx) {
      return !this.isPathInSelection(path, ix, iy, invertedSelection);
    }.bind(this));
  }.bind(this));
};

mpld3_LinkedBrushPlugin.prototype.end = function() {
  this.allObjects.selectAll("path").classed("mpld3-hidden", false);
};

mpld3_LinkedBrushPlugin.prototype.draw = function() {
  mpld3.insert_css("#" + this.fig.figid + " path.mpld3-hidden", {
    stroke: "#ccc !important",
    fill: "#ccc !important"
  });
  var pathCollection = mpld3.get_element(this.props.id);
  if (!pathCollection) {
    throw new Error("[LinkedBrush] Could not find path collection");
  }
  if (!("offsets" in pathCollection.props)) {
    throw new Error("[LinkedBrush] Figure is not a scatter plot.");
  }
  this.objectClass = "mpld3-brushtarget-" + pathCollection.props[this.dataKey];
  this.pathCollectionsByAxes = this.fig.axes.map(function(axes) {
    return axes.elements.map(function(el) {
      if (el.props[this.dataKey] == pathCollection.props[this.dataKey]) {
        el.group.classed(this.objectClass, true);
        return el;
      }
    }.bind(this)).filter(function(d) {
      return d;
    });
  }.bind(this));
  this.objectsByAxes = this.fig.axes.map(function(axes) {
    return axes.axes.selectAll("." + this.objectClass);
  }.bind(this));
  this.allObjects = this.fig.canvas.selectAll("." + this.objectClass);
};

mpld3.register_plugin("mouseposition", MousePositionPlugin);

MousePositionPlugin.prototype = Object.create(mpld3.Plugin.prototype);

MousePositionPlugin.prototype.constructor = MousePositionPlugin;

MousePositionPlugin.prototype.requiredProps = [];

MousePositionPlugin.prototype.defaultProps = {
  fontsize: 12,
  fmt: ".3g"
};

function MousePositionPlugin(fig, props) {
  mpld3.Plugin.call(this, fig, props);
}

MousePositionPlugin.prototype.draw = function() {
  var fig = this.fig;
  var fmt = d3.format(this.props.fmt);
  var coords = fig.canvas.append("text").attr("class", "mpld3-coordinates").style("text-anchor", "end").style("font-size", this.props.fontsize).attr("x", this.fig.width - 5).attr("y", this.fig.height - 5);
  for (var i = 0; i < this.fig.axes.length; i++) {
    var update_coords = function() {
      var ax = fig.axes[i];
      return function() {
        var pos = d3.mouse(this), x = ax.x.invert(pos[0]), y = ax.y.invert(pos[1]);
        coords.text("(" + fmt(x) + ", " + fmt(y) + ")");
      };
    }();
    fig.axes[i].baseaxes.on("mousemove", update_coords).on("mouseout", function() {
      coords.text("");
    });
  }
};

mpld3.Figure = mpld3_Figure;

mpld3_Figure.prototype = Object.create(mpld3_PlotElement.prototype);

mpld3_Figure.prototype.constructor = mpld3_Figure;

mpld3_Figure.prototype.requiredProps = [ "width", "height" ];

mpld3_Figure.prototype.defaultProps = {
  data: {},
  axes: [],
  plugins: [ {
    type: "reset"
  }, {
    type: "zoom"
  }, {
    type: "boxzoom"
  } ]
};

function mpld3_Figure(figid, props) {
  mpld3_PlotElement.call(this, null, props);
  this.figid = figid;
  this.width = this.props.width;
  this.height = this.props.height;
  this.data = this.props.data;
  this.buttons = [];
  this.root = d3.select("#" + figid).append("div").style("position", "relative");
  this.axes = [];
  for (var i = 0; i < this.props.axes.length; i++) this.axes.push(new mpld3_Axes(this, this.props.axes[i]));
  this.plugins = [];
  this.pluginsByType = {};
  this.props.plugins.forEach(function(plugin) {
    this.addPlugin(plugin);
  }.bind(this));
  this.toolbar = new mpld3.Toolbar(this, {
    buttons: this.buttons
  });
}

mpld3_Figure.prototype.addPlugin = function(pluginInfo) {
  if (!pluginInfo.type) {
    return console.warn("unspecified plugin type. Skipping this");
  }
  var plugin;
  if (pluginInfo.type in mpld3.plugin_map) {
    plugin = mpld3.plugin_map[pluginInfo.type];
  } else {
    return console.warn("Skipping unrecognized plugin: " + plugin);
  }
  if (pluginInfo.clear_toolbar || pluginInfo.buttons) {
    console.warn("DEPRECATION WARNING: " + "You are using pluginInfo.clear_toolbar or pluginInfo, which " + "have been deprecated. Please see the build-in plugins for the new " + "method to add buttons, otherwise contact the mpld3 maintainers.");
  }
  var pluginInfoNoType = mpld3_cloneObj(pluginInfo);
  delete pluginInfoNoType.type;
  var pluginInstance = new plugin(this, pluginInfoNoType);
  this.plugins.push(pluginInstance);
  this.pluginsByType[pluginInfo.type] = pluginInstance;
};

mpld3_Figure.prototype.draw = function() {
  mpld3.insert_css("div#" + this.figid, {
    "font-family": "Helvetica, sans-serif"
  });
  this.canvas = this.root.append("svg:svg").attr("class", "mpld3-figure").attr("width", this.width).attr("height", this.height);
  for (var i = 0; i < this.axes.length; i++) {
    this.axes[i].draw();
  }
  this.disableZoom();
  for (var i = 0; i < this.plugins.length; i++) {
    this.plugins[i].draw();
  }
  this.toolbar.draw();
};

mpld3_Figure.prototype.resetBrushForOtherAxes = function(currentAxid) {
  this.axes.forEach(function(axes) {
    if (axes.axid != currentAxid) {
      axes.resetBrush();
    }
  });
};

mpld3_Figure.prototype.updateLinkedBrush = function(selection) {
  if (!this.pluginsByType.linkedbrush) {
    return;
  }
  this.pluginsByType.linkedbrush.update(selection);
};

mpld3_Figure.prototype.endLinkedBrush = function() {
  if (!this.pluginsByType.linkedbrush) {
    return;
  }
  this.pluginsByType.linkedbrush.end();
};

mpld3_Figure.prototype.reset = function(duration) {
  this.axes.forEach(function(axes) {
    axes.reset();
  });
};

mpld3_Figure.prototype.enableLinkedBrush = function() {
  this.axes.forEach(function(axes) {
    axes.enableLinkedBrush();
  });
};

mpld3_Figure.prototype.disableLinkedBrush = function() {
  this.axes.forEach(function(axes) {
    axes.disableLinkedBrush();
  });
};

mpld3_Figure.prototype.enableBoxzoom = function() {
  this.axes.forEach(function(axes) {
    axes.enableBoxzoom();
  });
};

mpld3_Figure.prototype.disableBoxzoom = function() {
  this.axes.forEach(function(axes) {
    axes.disableBoxzoom();
  });
};

mpld3_Figure.prototype.enableZoom = function() {
  this.axes.forEach(function(axes) {
    axes.enableZoom();
  });
};

mpld3_Figure.prototype.disableZoom = function() {
  this.axes.forEach(function(axes) {
    axes.disableZoom();
  });
};

mpld3_Figure.prototype.toggleZoom = function() {
  if (this.isZoomEnabled) {
    this.disableZoom();
  } else {
    this.enableZoom();
  }
};

mpld3_Figure.prototype.setTicks = function(xy, nr, format) {
  this.axes.forEach(function(axes) {
    axes.setTicks(xy, nr, format);
  });
};

mpld3_Figure.prototype.setXTicks = function(nr, format) {
  this.setTicks("x", nr, format);
};

mpld3_Figure.prototype.setYTicks = function(nr, format) {
  this.setTicks("y", nr, format);
};

mpld3_Figure.prototype.removeNaN = function(data) {
  output = output.map(function(offsets) {
    return offsets.map(function(value) {
      if (typeof value == "number" && isNaN(value)) {
        return 0;
      } else {
        return value;
      }
    });
  });
};

mpld3_Figure.prototype.parse_offsets = function(data) {
  return data.map(function(offsets) {
    return offsets.map(function(value) {
      if (typeof value == "number" && isNaN(value)) {
        return 0;
      } else {
        return value;
      }
    });
  });
};

mpld3_Figure.prototype.get_data = function(data) {
  var output = data;
  if (data === null || typeof data === "undefined") {
    output = null;
  } else if (typeof data === "string") {
    output = this.data[data];
  }
  return output;
};

mpld3.PlotElement = mpld3_PlotElement;

function mpld3_PlotElement(parent, props) {
  this.parent = isUndefinedOrNull(parent) ? null : parent;
  this.props = isUndefinedOrNull(props) ? {} : this.processProps(props);
  this.fig = parent instanceof mpld3_Figure ? parent : parent && "fig" in parent ? parent.fig : null;
  this.ax = parent instanceof mpld3_Axes ? parent : parent && "ax" in parent ? parent.ax : null;
}

mpld3_PlotElement.prototype.requiredProps = [];

mpld3_PlotElement.prototype.defaultProps = {};

mpld3_PlotElement.prototype.processProps = function(props) {
  props = mpld3_cloneObj(props);
  var finalProps = {};
  var this_name = this.name();
  this.requiredProps.forEach(function(p) {
    if (!(p in props)) {
      throw "property '" + p + "' " + "must be specified for " + this_name;
    }
    finalProps[p] = props[p];
    delete props[p];
  });
  for (var p in this.defaultProps) {
    if (p in props) {
      finalProps[p] = props[p];
      delete props[p];
    } else {
      finalProps[p] = this.defaultProps[p];
    }
  }
  if ("id" in props) {
    finalProps.id = props.id;
    delete props.id;
  } else if (!("id" in finalProps)) {
    finalProps.id = mpld3.generateId();
  }
  for (var p in props) {
    console.warn("Unrecognized property '" + p + "' " + "for object " + this.name() + " (value = " + props[p] + ").");
  }
  return finalProps;
};

mpld3_PlotElement.prototype.name = function() {
  var funcNameRegex = /function (.{1,})\(/;
  var results = funcNameRegex.exec(this.constructor.toString());
  return results && results.length > 1 ? results[1] : "";
};

if (typeof module === "object" && module.exports) {
  module.exports = mpld3;
} else {
  this.mpld3 = mpld3;
}

console.log("Loaded mpld3 version " + mpld3.version);