describe('Charts', function () {

  var
    width = 480,
    height = 320,
    a, b, options, defaults;

  defaults = {
    width : 480,
    height : 320,
    color : "rgb(192,216,0)",
    context : null,
    data : null,
    fill : false,
    fillColor : null,
    fillOpacity : 0.4,
    fillStyle : "rgba(192,216,0,0.4)",
    fontColor : "#545454",
    fontSize : 7.5,
    htmlText : true,
    lineWidth : 2,
    shadowSize : 4,
    show : false,
    stacked : false,
    textEnabled : true,
    xScale : function (x) { return x; },
    yScale : function (y) { return height - y; }
  };

  /**
   * @param skip bool  Skip test against development version (use this when developing test)
   */
  function drawTest (data, o, skip) {
    options.data = data;
    if (o) _.extend(options, o);

    if (!skip) TestFlotr.graphTypes.lines.draw(options);
    options.context = b.getContext('2d');
    StableFlotr.graphTypes.lines.draw(options);

    expect(b).toImageDiffEqual(a);
  }

  describe('Lines', function () {

    beforeEach(function () {
      options = _.clone(defaults);
    });

    /*
    describe('Data', function () {
      it('gets a range', function () {
        options.stacked = true;
        options.data = [[0, 0], [240, 160], [480, 320]];
        range = TestFlotr.graphTypes.lines.range(options);
        expect(range.min).toEqual(0);
        expect(range.max).toEqual(320);
      });
    });
    */

    describe('Draw', function () {

      beforeEach(function () {
        this.addMatchers(imagediff.jasmine);
        a = imagediff.createCanvas(width, height);
        b = imagediff.createCanvas(width, height);
        options.context = a.getContext('2d');
      });

      it('draws a line chart', function () {
        drawTest([
          [0, 0],
          [240, 300],
          [480, 0]
        ]);
      });

      it('skips null values', function () {
        drawTest([
          [0, 0],
          [100, 50],
          [200, null],
          [300, 150],
          [400, 200],
          [480, 240]
        ]);
      });

      it('draws two lines', function () {
        // First line
        drawTest([[0, 0], [240, 160], [480, 320]]);

        // Second Line
        options.context = a.getContext('2d');
        drawTest([[0, 320], [240, 160], [480, 0]]);
      });

      it('fills a line', function () {
        drawTest([
          [0, 0],
          [240, 300],
          [480, 0]
        ], {
          fill : true
        });
      });

      it('draws no shadow', function () {
        drawTest([
          [0, 0],
          [240, 300],
          [480, 0]
        ], {
          shadowSize : 0
        });
      });
    });
  });
});
