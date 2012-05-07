(function () {

Flotr.ExampleList.add({
  key : 'test-boundaries',
  name : 'Test Boundaries',
  callback : test_boundaries
});

function test_boundaries (container) {

  var
    d1 = [[0, 0], [5, 0], [6, 10], [9, 10]], // First data series
    i, graph;

  // Draw Graph
  graph = Flotr.draw(container, [ d1 ], {
    title : 'test',
    xaxis: {
      minorTickFreq: 4
    },
    lines: { 
      lineWidth : 2
    },
    grid: {
      outlineWidth : 2,
      minorVerticalLines: true
    }
  });
}

})();
