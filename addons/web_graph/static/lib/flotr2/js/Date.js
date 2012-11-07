/**
 * Flotr Date
 */
Flotr.Date = {

  set : function (date, name, mode, value) {
    mode = mode || 'UTC';
    name = 'set' + (mode === 'UTC' ? 'UTC' : '') + name;
    date[name](value);
  },

  get : function (date, name, mode) {
    mode = mode || 'UTC';
    name = 'get' + (mode === 'UTC' ? 'UTC' : '') + name;
    return date[name]();
  },

  format: function(d, format, mode) {
    if (!d) return;

    // We should maybe use an "official" date format spec, like PHP date() or ColdFusion 
    // http://fr.php.net/manual/en/function.date.php
    // http://livedocs.adobe.com/coldfusion/8/htmldocs/help.html?content=functions_c-d_29.html
    var
      get = this.get,
      tokens = {
        h: get(d, 'Hours', mode).toString(),
        H: leftPad(get(d, 'Hours', mode)),
        M: leftPad(get(d, 'Minutes', mode)),
        S: leftPad(get(d, 'Seconds', mode)),
        s: get(d, 'Milliseconds', mode),
        d: get(d, 'Date', mode).toString(),
        m: (get(d, 'Month') + 1).toString(),
        y: get(d, 'FullYear').toString(),
        b: Flotr.Date.monthNames[get(d, 'Month', mode)]
      };

    function leftPad(n){
      n += '';
      return n.length == 1 ? "0" + n : n;
    }
    
    var r = [], c,
        escape = false;
    
    for (var i = 0; i < format.length; ++i) {
      c = format.charAt(i);
      
      if (escape) {
        r.push(tokens[c] || c);
        escape = false;
      }
      else if (c == "%")
        escape = true;
      else
        r.push(c);
    }
    return r.join('');
  },
  getFormat: function(time, span) {
    var tu = Flotr.Date.timeUnits;
         if (time < tu.second) return "%h:%M:%S.%s";
    else if (time < tu.minute) return "%h:%M:%S";
    else if (time < tu.day)    return (span < 2 * tu.day) ? "%h:%M" : "%b %d %h:%M";
    else if (time < tu.month)  return "%b %d";
    else if (time < tu.year)   return (span < tu.year) ? "%b" : "%b %y";
    else                       return "%y";
  },
  formatter: function (v, axis) {
    var
      options = axis.options,
      scale = Flotr.Date.timeUnits[options.timeUnit],
      d = new Date(v * scale);

    // first check global format
    if (axis.options.timeFormat)
      return Flotr.Date.format(d, options.timeFormat, options.timeMode);
    
    var span = (axis.max - axis.min) * scale,
        t = axis.tickSize * Flotr.Date.timeUnits[axis.tickUnit];

    return Flotr.Date.format(d, Flotr.Date.getFormat(t, span), options.timeMode);
  },
  generator: function(axis) {

     var
      set       = this.set,
      get       = this.get,
      timeUnits = this.timeUnits,
      spec      = this.spec,
      options   = axis.options,
      mode      = options.timeMode,
      scale     = timeUnits[options.timeUnit],
      min       = axis.min * scale,
      max       = axis.max * scale,
      delta     = (max - min) / options.noTicks,
      ticks     = [],
      tickSize  = axis.tickSize,
      tickUnit,
      formatter, i;

    // Use custom formatter or time tick formatter
    formatter = (options.tickFormatter === Flotr.defaultTickFormatter ?
      this.formatter : options.tickFormatter
    );

    for (i = 0; i < spec.length - 1; ++i) {
      var d = spec[i][0] * timeUnits[spec[i][1]];
      if (delta < (d + spec[i+1][0] * timeUnits[spec[i+1][1]]) / 2 && d >= tickSize)
        break;
    }
    tickSize = spec[i][0];
    tickUnit = spec[i][1];

    // special-case the possibility of several years
    if (tickUnit == "year") {
      tickSize = Flotr.getTickSize(options.noTicks*timeUnits.year, min, max, 0);

      // Fix for 0.5 year case
      if (tickSize == 0.5) {
        tickUnit = "month";
        tickSize = 6;
      }
    }

    axis.tickUnit = tickUnit;
    axis.tickSize = tickSize;

    var
      d = new Date(min);

    var step = tickSize * timeUnits[tickUnit];

    function setTick (name) {
      set(d, name, mode, Flotr.floorInBase(
        get(d, name, mode), tickSize
      ));
    }

    switch (tickUnit) {
      case "millisecond": setTick('Milliseconds'); break;
      case "second": setTick('Seconds'); break;
      case "minute": setTick('Minutes'); break;
      case "hour": setTick('Hours'); break;
      case "month": setTick('Month'); break;
      case "year": setTick('FullYear'); break;
    }
    
    // reset smaller components
    if (step >= timeUnits.second)  set(d, 'Milliseconds', mode, 0);
    if (step >= timeUnits.minute)  set(d, 'Seconds', mode, 0);
    if (step >= timeUnits.hour)    set(d, 'Minutes', mode, 0);
    if (step >= timeUnits.day)     set(d, 'Hours', mode, 0);
    if (step >= timeUnits.day * 4) set(d, 'Date', mode, 1);
    if (step >= timeUnits.year)    set(d, 'Month', mode, 0);

    var carry = 0, v = NaN, prev;
    do {
      prev = v;
      v = d.getTime();
      ticks.push({ v: v / scale, label: formatter(v / scale, axis) });
      if (tickUnit == "month") {
        if (tickSize < 1) {
          /* a bit complicated - we'll divide the month up but we need to take care of fractions
           so we don't end up in the middle of a day */
          set(d, 'Date', mode, 1);
          var start = d.getTime();
          set(d, 'Month', mode, get(d, 'Month', mode) + 1)
          var end = d.getTime();
          d.setTime(v + carry * timeUnits.hour + (end - start) * tickSize);
          carry = get(d, 'Hours', mode)
          set(d, 'Hours', mode, 0);
        }
        else
          set(d, 'Month', mode, get(d, 'Month', mode) + tickSize);
      }
      else if (tickUnit == "year") {
        set(d, 'FullYear', mode, get(d, 'FullYear', mode) + tickSize);
      }
      else
        d.setTime(v + step);

    } while (v < max && v != prev);

    return ticks;
  },
  timeUnits: {
    millisecond: 1,
    second: 1000,
    minute: 1000 * 60,
    hour:   1000 * 60 * 60,
    day:    1000 * 60 * 60 * 24,
    month:  1000 * 60 * 60 * 24 * 30,
    year:   1000 * 60 * 60 * 24 * 365.2425
  },
  // the allowed tick sizes, after 1 year we use an integer algorithm
  spec: [
    [1, "millisecond"], [20, "millisecond"], [50, "millisecond"], [100, "millisecond"], [200, "millisecond"], [500, "millisecond"], 
    [1, "second"],   [2, "second"],  [5, "second"], [10, "second"], [30, "second"], 
    [1, "minute"],   [2, "minute"],  [5, "minute"], [10, "minute"], [30, "minute"], 
    [1, "hour"],     [2, "hour"],    [4, "hour"],   [8, "hour"],    [12, "hour"],
    [1, "day"],      [2, "day"],     [3, "day"],
    [0.25, "month"], [0.5, "month"], [1, "month"],  [2, "month"],   [3, "month"], [6, "month"],
    [1, "year"]
  ],
  monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
};
