/**
 * Flotr Series Library
 */

(function () {

var
  _ = Flotr._;

function Series (o) {
  _.extend(this, o);
}

Series.prototype = {

  getRange: function () {

    var
      data = this.data,
      length = data.length,
      xmin = Number.MAX_VALUE,
      ymin = Number.MAX_VALUE,
      xmax = -Number.MAX_VALUE,
      ymax = -Number.MAX_VALUE,
      xused = false,
      yused = false,
      x, y, i;

    if (length < 0 || this.hide) return false;

    for (i = 0; i < length; i++) {
      x = data[i][0];
      y = data[i][1];
      if (x < xmin) { xmin = x; xused = true; }
      if (x > xmax) { xmax = x; xused = true; }
      if (y < ymin) { ymin = y; yused = true; }
      if (y > ymax) { ymax = y; yused = true; }
    }

    return {
      xmin : xmin,
      xmax : xmax,
      ymin : ymin,
      ymax : ymax,
      xused : xused,
      yused : yused
    };
  }
};

_.extend(Series, {
  /**
   * Collects dataseries from input and parses the series into the right format. It returns an Array 
   * of Objects each having at least the 'data' key set.
   * @param {Array, Object} data - Object or array of dataseries
   * @return {Array} Array of Objects parsed into the right format ({(...,) data: [[x1,y1], [x2,y2], ...] (, ...)})
   */
  getSeries: function(data){
    return _.map(data, function(s){
      var series;
      if (s.data) {
        series = new Series();
        _.extend(series, s);
      } else {
        series = new Series({data:s});
      }
      return series;
    });
  }
});

Flotr.Series = Series;

})();
