(function () {

var ExampleList = function () {

  // Map of examples.
  this.examples = {};

};

ExampleList.prototype = {

  add : function (example) {
    this.examples[example.key] = example;
  },

  get : function (key) {
    return key ? (this.examples[key] || null) : this.examples;
  },

  getType : function (type) {
    return Flotr._.select(this.examples, function (example) {
      return (example.type === type);
    });
  }
}

Flotr.ExampleList = new ExampleList();

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic',
  name : 'Basic',
  callback : basic
});

function basic (container) {

  var
    d1 = [[0, 3], [4, 8], [8, 5], [9, 13]], // First data series
    d2 = [],                                // Second data series
    i, graph;

  // Generate first data set
  for (i = 0; i < 14; i += 0.5) {
    d2.push([i, Math.sin(i)]);
  }

  // Draw Graph
  graph = Flotr.draw(container, [ d1, d2 ], {
    xaxis: {
      minorTickFreq: 4
    }, 
    grid: {
      minorVerticalLines: true
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-stacked',
  name : 'Basic Stacked',
  callback : basic_stacked,
  type : 'test'
});

function basic_stacked (container) {

  var
    d1 = [[0, 3], [4, 8], [8, 2], [9, 3]], // First data series
    d2 = [[0, 2], [4, 3], [8, 8], [9, 4]], // Second data series
    i, graph;

  // Draw Graph
  graph = Flotr.draw(container, [ d1, d2 ], {
    lines: {
      show : true,
      stacked: true
    },
    xaxis: {
      minorTickFreq: 4
    }, 
    grid: {
      minorVerticalLines: true
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-stepped',
  name : 'Basic Stepped',
  callback : basic_stepped,
  type : 'test'
});

function basic_stepped (container) {

  var
    d1 = [[0, 3], [4, 8], [8, 5], [9, 13]], // First data series
    d2 = [],                                // Second data series
    i, graph;

  // Generate first data set
  for (i = 0; i < 14; i += 0.5) {
    d2.push([i, Math.sin(i)]);
  }

  // Draw Graph
  graph = Flotr.draw(container, [ d1, d2 ], {
    lines: {
      steps : true,
      show : true
    },
    xaxis: {
      minorTickFreq: 4
    }, 
    yaxis: {
      autoscale: true
    },
    grid: {
      minorVerticalLines: true
    },
    mouse : {
      track : true,
      relative : true
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-axis',
  name : 'Basic Axis',
  callback : basic_axis
});

function basic_axis (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    d4 = [],
    d5 = [],                        // Data
    ticks = [[ 0, "Lower"], 10, 20, 30, [40, "Upper"]], // Ticks for the Y-Axis
    graph;
        
  for(var i = 0; i <= 10; i += 0.1){
    d1.push([i, 4 + Math.pow(i,1.5)]);
    d2.push([i, Math.pow(i,3)]);
    d3.push([i, i*5+3*Math.sin(i*4)]);
    d4.push([i, i]);
    if( i.toFixed(1)%1 == 0 ){
      d5.push([i, 2*i]);
    }
  }
        
  d3[30][1] = null;
  d3[31][1] = null;

  function ticksFn (n) { return '('+n+')'; }

  graph = Flotr.draw(container, [ 
      { data : d1, label : 'y = 4 + x^(1.5)', lines : { fill : true } }, 
      { data : d2, label : 'y = x^3'}, 
      { data : d3, label : 'y = 5x + 3sin(4x)'}, 
      { data : d4, label : 'y = x'},
      { data : d5, label : 'y = 2x', lines : { show : true }, points : { show : true } }
    ], {
      xaxis : {
        noTicks : 7,              // Display 7 ticks.
        tickFormatter : ticksFn,  // Displays tick values between brackets.
        min : 1,                  // Part of the series is not displayed.
        max : 7.5                 // Part of the series is not displayed.
      },
      yaxis : {
        ticks : ticks,            // Set Y-Axis ticks
        max : 40                  // Maximum value along Y-Axis
      },
      grid : {
        verticalLines : false,
        backgroundColor : {
          colors : [[0,'#fff'], [1,'#ccc']],
          start : 'top',
          end : 'bottom'
        }
      },
      legend : {
        position : 'nw'
      },
      title : 'Basic Axis example',
      subtitle : 'This is a subtitle'
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-bars',
  name : 'Basic Bars',
  callback : basic_bars
});

Flotr.ExampleList.add({
  key : 'basic-bars-horizontal',
  name : 'Horizontal Bars',
  args : [true],
  callback : basic_bars,
  tolerance : 5
});

function basic_bars (container, horizontal) {

  var
    horizontal = (horizontal ? true : false), // Show horizontal bars
    d1 = [],                                  // First data series
    d2 = [],                                  // Second data series
    point,                                    // Data point variable declaration
    i;

  for (i = 0; i < 4; i++) {

    if (horizontal) { 
      point = [Math.ceil(Math.random()*10), i];
    } else {
      point = [i, Math.ceil(Math.random()*10)];
    }

    d1.push(point);
        
    if (horizontal) { 
      point = [Math.ceil(Math.random()*10), i+0.5];
    } else {
      point = [i+0.5, Math.ceil(Math.random()*10)];
    }

    d2.push(point);
  };
              
  // Draw the graph
  Flotr.draw(
    container,
    [d1, d2],
    {
      bars : {
        show : true,
        horizontal : horizontal,
        shadowSize : 0,
        barWidth : 0.5
      },
      mouse : {
        track : true,
        relative : true
      },
      yaxis : {
        min : 0,
        autoscaleMargin : 1
      }
    }
  );
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-bar-stacked',
  name : 'Stacked Bars',
  callback : bars_stacked
});

Flotr.ExampleList.add({
  key : 'basic-stacked-horizontal',
  name : 'Stacked Horizontal Bars',
  args : [true],
  callback : bars_stacked,
  tolerance : 5
});

function bars_stacked (container, horizontal) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    graph, i;

  for (i = -10; i < 10; i++) {
    if (horizontal) {
      d1.push([Math.random(), i]);
      d2.push([Math.random(), i]);
      d3.push([Math.random(), i]);
    } else {
      d1.push([i, Math.random()]);
      d2.push([i, Math.random()]);
      d3.push([i, Math.random()]);
    }
  }

  graph = Flotr.draw(container,[
    { data : d1, label : 'Serie 1' },
    { data : d2, label : 'Serie 2' },
    { data : d3, label : 'Serie 3' }
  ], {
    legend : {
      backgroundColor : '#D2E8FF' // Light blue 
    },
    bars : {
      show : true,
      stacked : true,
      horizontal : horizontal,
      barWidth : 0.6,
      lineWidth : 1,
      shadowSize : 0
    },
    grid : {
      verticalLines : horizontal,
      horizontalLines : !horizontal
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-pie',
  name : 'Basic Pie',
  callback : basic_pie
});

function basic_pie (container) {

  var
    d1 = [[0, 4]],
    d2 = [[0, 3]],
    d3 = [[0, 1.03]],
    d4 = [[0, 3.5]],
    graph;
  
  graph = Flotr.draw(container, [
    { data : d1, label : 'Comedy' },
    { data : d2, label : 'Action' },
    { data : d3, label : 'Romance',
      pie : {
        explode : 50
      }
    },
    { data : d4, label : 'Drama' }
  ], {
    HtmlText : false,
    grid : {
      verticalLines : false,
      horizontalLines : false
    },
    xaxis : { showLabels : false },
    yaxis : { showLabels : false },
    pie : {
      show : true, 
      explode : 6
    },
    mouse : { track : true },
    legend : {
      position : 'se',
      backgroundColor : '#D2E8FF'
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-radar',
  name : 'Basic Radar',
  callback : basic_radar
});

function basic_radar (container) {

  // Fill series s1 and s2.
  var
    s1 = { label : 'Actual', data : [[0, 3], [1, 8], [2, 5], [3, 5], [4, 3], [5, 9]] },
    s2 = { label : 'Target', data : [[0, 8], [1, 7], [2, 8], [3, 2], [4, 4], [5, 7]] },
    graph, ticks;

  // Radar Labels
  ticks = [
    [0, "Statutory"],
    [1, "External"],
    [2, "Videos"],
    [3, "Yippy"],
    [4, "Management"],
    [5, "oops"]
  ];
    
  // Draw the graph.
  graph = Flotr.draw(container, [ s1, s2 ], {
    radar : { show : true}, 
    grid  : { circular : true, minorHorizontalLines : true}, 
    yaxis : { min : 0, max : 10, minorTickFreq : 2}, 
    xaxis : { ticks : ticks}
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-bubble',
  name : 'Basic Bubble',
  callback : basic_bubble
});

function basic_bubble (container) {

  var
    d1 = [],
    d2 = [],
    point, graph, i;
      
  for (i = 0; i < 10; i++ ){
    point = [i, Math.ceil(Math.random()*10), Math.ceil(Math.random()*10)];
    d1.push(point);
    
    point = [i, Math.ceil(Math.random()*10), Math.ceil(Math.random()*10)];
    d2.push(point);
  }
  
  // Draw the graph
  graph = Flotr.draw(container, [d1, d2], {
    bubbles : { show : true, baseRadius : 5 },
    xaxis   : { min : -4, max : 14 },
    yaxis   : { min : -4, max : 14 }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-candle',
  name : 'Basic Candle',
  callback : basic_candle
});

function basic_candle (container) {

  var
    d1 = [],
    price = 3.206,
    graph,
    i, a, b, c;

  for (i = 0; i < 50; i++) {
      a = Math.random();
      b = Math.random();
      c = (Math.random() * (a + b)) - b;
      d1.push([i, price, price + a, price - b, price + c]);
      price = price + c;
  }
    
  // Graph
  graph = Flotr.draw(container, [ d1 ], { 
    candles : { show : true, candleWidth : 0.6 },
    xaxis   : { noTicks : 10 }
  });
}

})();


(function () {

Flotr.ExampleList.add({
  key : 'basic-legend',
  name : 'Basic Legend',
  callback : basic_legend
});

function basic_legend (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    data,
    graph, i;

  // Data Generation
  for (i = 0; i < 15; i += 0.5) {
    d1.push([i, i + Math.sin(i+Math.PI)]);
    d2.push([i, i]);
    d3.push([i, 15-Math.cos(i)]);
  }

  data = [
    { data : d1, label :'x + sin(x+&pi;)' },
    { data : d2, label :'x' },
    { data : d3, label :'15 - cos(x)' }
  ];


  // This function prepend each label with 'y = '
  function labelFn (label) {
    return 'y = ' + label;
  }

  // Draw graph
  graph = Flotr.draw(container, data, {
    legend : {
      position : 'se',            // Position the legend 'south-east'.
      labelFormatter : labelFn,   // Format the labels.
      backgroundColor : '#D2E8FF' // A light blue background color.
    },
    HtmlText : false
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'mouse-tracking',
  name : 'Mouse Tracking',
  callback : mouse_tracking
});

function mouse_tracking (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    graph, i;

  for (i = 0; i < 20; i += 0.5) {
    d1.push([i, 2*i]);
    d2.push([i, i*1.5+1.5*Math.sin(i)]);
    d3.push([i, 3*Math.cos(i)+10]);
  }

  graph = Flotr.draw(
    container, 
    [
      {
        data : d1,
        mouse : { track : false } // Disable mouse tracking for d1
      },
      d2,
      d3
    ],
    {
      mouse : {
        track           : true, // Enable mouse tracking
        lineColor       : 'purple',
        relative        : true,
        position        : 'ne',
        sensibility     : 1,
        trackDecimals   : 2,
        trackFormatter  : function (o) { return 'x = ' + o.x +', y = ' + o.y; }
      },
      crosshair : {
        mode : 'xy'
      }
    }
  );

};      

})();

(function () {

Flotr.ExampleList.add({
  key : 'mouse-zoom',
  name : 'Mouse Zoom',
  callback : mouse_zoom,
  description : "<p>Select an area of the graph to zoom.  Click to reset the chart.</p>"
});

function mouse_zoom (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    options,
    graph,
    i;

  for (i = 0; i < 40; i += 0.5) {
    d1.push([i, Math.sin(i)+3*Math.cos(i)]);
    d2.push([i, Math.pow(1.1, i)]);
    d3.push([i, 40 - i+Math.random()*10]);
  }
      
  options = {
    selection : { mode : 'x', fps : 30 },
    title : 'Mouse Zoom'
  };
    
  // Draw graph with default options, overwriting with passed options
  function drawGraph (opts) {

    // Clone the options, so the 'options' variable always keeps intact.
    var o = Flotr._.extend(Flotr._.clone(options), opts || {});

    // Return a new graph.
    return Flotr.draw(
      container,
      [ d1, d2, d3 ],
      o
    );
  }

  // Actually draw the graph.
  graph = drawGraph();      
    
  // Hook into the 'flotr:select' event.
  Flotr.EventAdapter.observe(container, 'flotr:select', function (area) {

    // Draw graph with new area
    f = drawGraph({
      xaxis: {min:area.x1, max:area.x2},
      yaxis: {min:area.y1, max:area.y2}
    });

  });
    
  // When graph is clicked, draw the graph with default area.
  Flotr.EventAdapter.observe(container, 'flotr:click', function () { drawGraph(); });
};

})();


(function () {

Flotr.ExampleList.add({
  key : 'mouse-drag',
  name : 'Mouse Drag',
  callback : mouse_drag
});

function mouse_drag (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    options,
    graph,
    start,
    i;

  for (i = -40; i < 40; i += 0.5) {
    d1.push([i, Math.sin(i)+3*Math.cos(i)]);
    d2.push([i, Math.pow(1.1, i)]);
    d3.push([i, 40 - i+Math.random()*10]);
  }
      
  options = {
    xaxis: {min: 0, max: 20},
      title : 'Mouse Drag'
  };

  // Draw graph with default options, overwriting with passed options
  function drawGraph (opts) {

    // Clone the options, so the 'options' variable always keeps intact.
    var o = Flotr._.extend(Flotr._.clone(options), opts || {});

    // Return a new graph.
    return Flotr.draw(
      container,
      [ d1, d2, d3 ],
      o
    );
  }

  graph = drawGraph();      

  function initializeDrag (e) {
    start = graph.getEventPosition(e);
    Flotr.EventAdapter.observe(document, 'mousemove', move);
    Flotr.EventAdapter.observe(document, 'mouseup', stopDrag);
  }

  function move (e) {
    var
      end     = graph.getEventPosition(e),
      xaxis   = graph.axes.x,
      offset  = start.x - end.x;

    graph = drawGraph({
      xaxis : {
        min : xaxis.min + offset,
        max : xaxis.max + offset
      }
    });
    // @todo: refector initEvents in order not to remove other observed events
    Flotr.EventAdapter.observe(graph.overlay, 'mousedown', initializeDrag);
  }

  function stopDrag () {
    Flotr.EventAdapter.stopObserving(document, 'mousemove', move);
  }

  Flotr.EventAdapter.observe(graph.overlay, 'mousedown', initializeDrag);

};

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-time',
  name : 'Basic Time',
  callback : basic_time,
  description : "<p>Select an area of the graph to zoom.  Click to reset the chart.</p>"
});

function basic_time (container) {

  var
    d1    = [],
    start = new Date("2009/01/01 01:00").getTime(),
    options,
    graph,
    i, x, o;

  for (i = 0; i < 100; i++) {
    x = start+(i*1000*3600*24*36.5);
    d1.push([x, i+Math.random()*30+Math.sin(i/20+Math.random()*2)*20+Math.sin(i/10+Math.random())*10]);
  }
        
  options = {
    xaxis : {
      mode : 'time', 
      labelsAngle : 45
    },
    selection : {
      mode : 'x'
    },
    HtmlText : false,
    title : 'Time'
  };
        
  // Draw graph with default options, overwriting with passed options
  function drawGraph (opts) {

    // Clone the options, so the 'options' variable always keeps intact.
    o = Flotr._.extend(Flotr._.clone(options), opts || {});

    // Return a new graph.
    return Flotr.draw(
      container,
      [ d1 ],
      o
    );
  }

  graph = drawGraph();      
        
  Flotr.EventAdapter.observe(container, 'flotr:select', function(area){
    // Draw selected area
    graph = drawGraph({
      xaxis : { min : area.x1, max : area.x2, mode : 'time', labelsAngle : 45 },
      yaxis : { min : area.y1, max : area.y2 }
    });
  });
        
  // When graph is clicked, draw the graph with default area.
  Flotr.EventAdapter.observe(container, 'flotr:click', function () { graph = drawGraph(); });
};      

})();

(function () {

Flotr.ExampleList.add({
  key : 'negative-values',
  name : 'Negative Values',
  callback : negative_values
});

function negative_values (container) {

  var
    d0    = [], // Line through y = 0
    d1    = [], // Random data presented as a scatter plot. 
    d2    = [], // A regression line for the scatter. 
    sx    = 0,
    sy    = 0,
    sxy   = 0,
    sxsq  = 0,
    xmean,
    ymean,
    alpha,
    beta,
    n, x, y;

  for (n = 0; n < 20; n++){

    x = n;
    y = x + Math.random()*8 - 15;

    d0.push([x, 0]);
    d1.push([x, y]);

    // Computations used for regression line
    sx += x;
    sy += y;
    sxy += x*y;
    sxsq += Math.pow(x,2);
  }

  xmean = sx/n;
  ymean = sy/n;
  beta  = ((n*sxy) - (sx*sy))/((n*sxsq)-(Math.pow(sx,2)));
  alpha = ymean - (beta * xmean);
  
  // Compute the regression line.
  for (n = 0; n < 20; n++){
    d2.push([n, alpha + beta*n])
  }     

  // Draw the graph
  graph = Flotr.draw(
    container, [ 
      { data : d0, shadowSize : 0, color : '#545454' }, // Horizontal
      { data : d1, label : 'y = x + (Math.random() * 8) - 15', points : { show : true } },  // Scatter
      { data : d2, label : 'y = ' + alpha.toFixed(2) + ' + ' + beta.toFixed(2) + '*x' }  // Regression
    ],
    {
      legend : { position : 'se', backgroundColor : '#D2E8FF' },
      title : 'Negative Values'
    }
  );
};

})();

(function () {

Flotr.ExampleList.add({
  key : 'click-example',
  name : 'Click Example',
  callback : click_example
});

function click_example (container) {

  var
    d1 = [[0,0]], // Point at origin
    options,
    graph;

  options = {
    xaxis: {min: 0, max: 15},
    yaxis: {min: 0, max: 15},
    lines: {show: true},
    points: {show: true},
    mouse: {track:true},
    title: 'Click Example'
  };

  graph = Flotr.draw(container, [d1], options);

  // Add a point to the series and redraw the graph
  Flotr.EventAdapter.observe(container, 'flotr:click', function(position){

    // Add a point to the series at the location of the click
    d1.push([position.x, position.y]);
    
    // Sort the series.
    d1 = d1.sort(function (a, b) { return a[0] - b[0]; });
    
    // Redraw the graph, with the new series.
    graph = Flotr.draw(container, [d1], options);
  });
};      

})();

(function () {

Flotr.ExampleList.add({
  key : 'download-image',
  name : 'Download Image',
  callback : download_image,
  description : '' + 
    '<form name="image-download" id="image-download" action="" onsubmit="return false">' +
      '<label><input type="radio" name="format" value="png" checked="checked" /> PNG</label>' +
      '<label><input type="radio" name="format" value="jpeg" /> JPEG</label>' +

      '<button name="to-image" onclick="CurrentExample(\'to-image\')">To Image</button>' +
      '<button name="download" onclick="CurrentExample(\'download\')">Download</button>' +
      '<button name="reset" onclick="CurrentExample(\'reset\')">Reset</button>' +
    '</form>'
});

function download_image (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    d4 = [],
    d5 = [],
    graph,
    i;
  
  for (i = 0; i <= 10; i += 0.1) {
    d1.push([i, 4 + Math.pow(i,1.5)]);
    d2.push([i, Math.pow(i,3)]);
    d3.push([i, i*5+3*Math.sin(i*4)]);
    d4.push([i, i]);
    if( i.toFixed(1)%1 == 0 ){
      d5.push([i, 2*i]);
    }
  }

  // Draw the graph
  graph = Flotr.draw(
    container,[ 
      {data:d1, label:'y = 4 + x^(1.5)', lines:{fill:true}}, 
      {data:d2, label:'y = x^3', yaxis:2}, 
      {data:d3, label:'y = 5x + 3sin(4x)'}, 
      {data:d4, label:'y = x'},
      {data:d5, label:'y = 2x', lines: {show: true}, points: {show: true}}
    ],{
      title: 'Download Image Example',
      subtitle: 'You can save me as an image',
      xaxis:{
        noTicks: 7, // Display 7 ticks.
        tickFormatter: function(n){ return '('+n+')'; }, // => displays tick values between brackets.
        min: 1,  // => part of the series is not displayed.
        max: 7.5, // => part of the series is not displayed.
        labelsAngle: 45,
        title: 'x Axis'
      },
      yaxis:{
        ticks: [[0, "Lower"], 10, 20, 30, [40, "Upper"]],
        max: 40,
        title: 'y = f(x)'
      },
      y2axis:{color:'#FF0000', max: 500, title: 'y = x^3'},
      grid:{
        verticalLines: false,
        backgroundColor: 'white'
      },
      HtmlText: false,
      legend: {
        position: 'nw'
      }
  });

  this.CurrentExample = function (operation) {

    var
      format = $('#image-download input:radio[name=format]:checked').val();
    if (Flotr.isIE && Flotr.isIE < 9) {
      alert(
        "Your browser doesn't allow you to get a bitmap image from the plot, " +
        "you can only get a VML image that you can use in Microsoft Office.<br />"
      );
    }

    if (operation == 'to-image') {
      graph.download.saveImage(format, null, null, true)
    } else if (operation == 'download') {
      graph.download.saveImage(format);
    } else if (operation == 'reset') {
      graph.download.restoreCanvas();
    }
  };

  return graph;
};

})();

(function () {

Flotr.ExampleList.add({
  key : 'download-data',
  name : 'Download Data',
  callback : download_data
});

function download_data (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    d4 = [],
    d5 = [],
    graph,
    i,x;
  
  for (i = 0; i <= 100; i += 1) {
    x = i / 10;
    d1.push([x, 4 + Math.pow(x,1.5)]);
    d2.push([x, Math.pow(x,3)]);
    d3.push([x, i*5+3*Math.sin(x*4)]);
    d4.push([x, x]);
    if(x%1 === 0 ){
      d5.push([x, 2*x]);
    }
  }
          
  // Draw the graph.
  graph = Flotr.draw(
    container, [ 
      { data : d1, label : 'y = 4 + x^(1.5)', lines : { fill : true } },
      { data : d2, label : 'y = x^3' },
      { data : d3, label : 'y = 5x + 3sin(4x)' },
      { data : d4, label : 'y = x' },
      { data : d5, label : 'y = 2x', lines : { show : true }, points : { show : true } }
    ],{
      xaxis : {
        noTicks : 7,
        tickFormatter : function (n) { return '('+n+')'; },
        min: 1,   // Part of the series is not displayed.
        max: 7.5
      },
      yaxis : {
        ticks : [[ 0, "Lower"], 10, 20, 30, [40, "Upper"]],
        max : 40
      },
      grid : {
        verticalLines : false,
        backgroundColor : 'white'
      },
      legend : {
        position : 'nw'
      },
      spreadsheet : {
        show : true,
        tickFormatter : function (e) { return e+''; }
      }
  });
};

})();

(function () {

Flotr.ExampleList.add({
  key : 'advanced-titles',
  name : 'Advanced Titles',
  callback : advanced_titles
});

function advanced_titles (container) {

  var
    d1 = [],
    d2 = [],
    d3 = [],
    d4 = [],
    d5 = [],
    graph,
    i;

  for (i = 0; i <= 10; i += 0.1) {
    d1.push([i, 4 + Math.pow(i,1.5)]);
    d2.push([i, Math.pow(i,3)]);
    d3.push([i, i*5+3*Math.sin(i*4)]);
    d4.push([i, i]);
    if (i.toFixed(1)%1 == 0) {
      d5.push([i, 2*i]);
    }
  }

  // Draw the graph.
  graph = Flotr.draw(
    container,[ 
      { data : d1, label : 'y = 4 + x^(1.5)', lines : { fill : true } },
      { data : d2, label : 'y = x^3', yaxis : 2 },
      { data : d3, label : 'y = 5x + 3sin(4x)' },
      { data : d4, label : 'y = x' },
      { data : d5, label : 'y = 2x', lines : { show : true }, points : { show : true } }
    ], {
      title : 'Advanced Titles Example',
      subtitle : 'You can save me as an image',
      xaxis : {
        noTicks : 7,
        tickFormatter : function (n) { return '('+n+')'; },
        min : 1,
        max : 7.5,
        labelsAngle : 45,
        title : 'x Axis'
      },
      yaxis : {
        ticks : [[0, "Lower"], 10, 20, 30, [40, "Upper"]],
        max : 40,
        title : 'y = f(x)'
      },
      y2axis : { color : '#FF0000', max : 500, title : 'y = x^3' },
      grid : {
        verticalLines : false,
        backgroundColor : 'white'
      },
      HtmlText : false,
      legend : {
        position : 'nw'
      }
  });
};

})();

(function () {

Flotr.ExampleList.add({
  key : 'color-gradients',
  name : 'Color Gradients',
  callback : color_gradients
});

function color_gradients (container) {

  var
    bars = {
      data: [],
      bars: {
        show: true,
        barWidth: 0.8,
        lineWidth: 0,
        fillColor: {
          colors: ['#CB4B4B', '#fff'],
          start: 'top',
          end: 'bottom'
        },
        fillOpacity: 0.8
      }
    }, markers = {
      data: [],
      markers: {
        show: true,
        position: 'ct'
      }
    }, lines = {
      data: [],
      lines: {
        show: true,
        fillColor: ['#00A8F0', '#fff'],
        fill: true,
        fillOpacity: 1
      }
    },
    point,
    graph,
    i;
  
  for (i = 0; i < 8; i++) {
    point = [i, Math.ceil(Math.random() * 10)];
    bars.data.push(point);
    markers.data.push(point);
  }
  
  for (i = -1; i < 9; i += 0.01){
    lines.data.push([i, i*i/8+2]);
  }
  
  graph = Flotr.draw(
    container,
    [lines, bars, markers], {
      yaxis: {
        min: 0,
        max: 11
      },
      xaxis: {
        min: -0.5,
        max: 7.5
      },
      grid: {
        verticalLines: false,
        backgroundColor: ['#fff', '#ccc']
      }
    }
  );
};

})();


(function () {

Flotr.ExampleList.add({
  key : 'profile-bars',
  name : 'Profile Bars',
  type : 'profile',
  callback : profile_bars
});

/*
Flotr.ExampleList.add({
  key : 'basic-bars-horizontal',
  name : 'Horizontal Bars',
  args : [true],
  callback : basic_bars
});
*/

function profile_bars (container, horizontal) {

  var
    horizontal = (horizontal ? true : false), // Show horizontal bars
    d1 = [],                                  // First data series
    d2 = [],                                  // Second data series
    point,                                    // Data point variable declaration
    i;

  for (i = 0; i < 5000; i++) {

    if (horizontal) { 
      point = [Math.ceil(Math.random()*10), i];
    } else {
      point = [i, Math.ceil(Math.random()*10)];
    }

    d1.push(point);
        
    if (horizontal) { 
      point = [Math.ceil(Math.random()*10), i+0.5];
    } else {
      point = [i+0.5, Math.ceil(Math.random()*10)];
    }

    d2.push(point);
  };
              
  // Draw the graph
  Flotr.draw(
    container,
    [d1, d2],
    {
      bars : {
        show : true,
        horizontal : horizontal,
        barWidth : 0.5
      },
      mouse : {
        track : true,
        relative : true
      },
      yaxis : {
        min : 0,
        autoscaleMargin : 1
      }
    }
  );
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'basic-timeline',
  name : 'Basic Timeline',
  callback : basic_timeline
});

function basic_timeline (container) {

  var
    d1        = [[1, 4, 5]],
    d2        = [[3.2, 3, 4]],
    d3        = [[1.9, 2, 2], [5, 2, 3.3]],
    d4        = [[1.55, 1, 9]],
    d5        = [[5, 0, 2.3]],
    data      = [],
    timeline  = { show : true, barWidth : .5 },
    markers   = [],
    labels    = ['Obama', 'Bush', 'Clinton', 'Palin', 'McCain'],
    i, graph, point;

  // Timeline
  Flotr._.each([d1, d2, d3, d4, d5], function (d) {
    data.push({
      data : d,
      timeline : Flotr._.clone(timeline)
    });
  });

  // Markers
  Flotr._.each([d1, d2, d3, d4, d5], function (d) {
    point = d[0];
    markers.push([point[0], point[1]]);
  });
  data.push({
    data: markers,
    markers: {
      show: true,
      position: 'rm',
      fontSize: 11,
      labelFormatter : function (o) { return labels[o.index]; }
    }
  });
  
  // Draw Graph
  graph = Flotr.draw(container, data, {
    xaxis: {
      noTicks: 3,
      tickFormatter: function (x) {
        var
          x = parseInt(x),
          months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return months[(x-1)%12];
      }
    }, 
    yaxis: {
      showLabels : false
    },
    grid: {
      horizontalLines : false
    }
  });
}

})();

(function () {

Flotr.ExampleList.add({
  key : 'advanced-markers',
  name : 'Advanced Markers',
  callback : advanced_markers,
  timeout : 150
});

function advanced_markers (container) {

  var
    xmark = new Image(),
    checkmark = new Image(),
    bars = {
      data: [],
      bars: {
        show: true,
        barWidth: 0.6,
        lineWidth: 0,
        fillOpacity: 0.8
      }
    }, markers = {
      data: [],
      markers: {
        show: true,
        position: 'ct',
        labelFormatter: function (o) {
          return (o.y >= 5) ? checkmark : xmark;
        }
      }
    },
    flotr = Flotr,
    point,
    graph,
    i;


  for (i = 0; i < 8; i++) {
    point = [i, Math.ceil(Math.random() * 10)];
    bars.data.push(point);
    markers.data.push(point);
  }

  var runner = function () {
    if (!xmark.complete || !checkmark.complete) {
        setTimeout(runner, 50);
        return;
    }

    graph = flotr.draw(
      container,
      [bars, markers], {
        yaxis: {
          min: 0,
          max: 11
        },
        xaxis: {
          min: -0.5,
          max: 7.5
        },
        grid: {
          verticalLines: false
        }
      }
    );
  }

  xmark.onload = runner;
  xmark.src = 'images/xmark.png';
  checkmark.src = 'images/checkmark.png';
};

})();

