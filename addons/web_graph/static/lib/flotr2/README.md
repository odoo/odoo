Flotr2
======

The Canvas graphing library.

![Google Groups](http://groups.google.com/intl/en/images/logos/groups_logo_sm.gif)

http://groups.google.com/group/flotr2/

Please fork http://jsfiddle.net/cesutherland/ZFBj5/ with your question or bug reproduction case.


API
---

The API consists of a primary draw method which accepts a configuration object, helper methods, and several microlibs.

### Example

```javascript
  var
    // Container div:
    container = document.getElementById("flotr-example-graph"),
    // First data series:
    d1 = [[0, 3], [4, 8], [8, 5], [9, 13]],
    // Second data series:
    d2 = [],
    // A couple flotr configuration options:
    options = {
      xaxis: {
        minorTickFreq: 4
      }, 
      grid: {
        minorVerticalLines: true
      }
    },
    i, graph;

  // Generated second data set:
  for (i = 0; i < 14; i += 0.5) {
    d2.push([i, Math.sin(i)]);
  }

  // Draw the graph:
  graph = Flotr.draw(
    container,  // Container element
    [ d1, d2 ], // Array of data series
    options     // Configuration options
  );
```

### Microlibs

* [underscore.js](http://documentcloud.github.com/underscore/)
* [bean.js](https://github.com/fat/bean)

Extending
---------

Flotr may be extended by adding new plugins and graph types.

### Graph Types

Graph types define how a particular chart is rendered.  Examples include line, bar, pie.

Existing graph types are found in `js/types/`.

### Plugins

Plugins extend the core of flotr with new functionality.  They can add interactions, new decorations, etc.  Examples 
include titles, labels and selection.

The plugins included are found in `js/plugins/`.

Development
-----------

This project uses [smoosh](https://github.com/fat/smoosh) to build and [jasmine](http://pivotal.github.com/jasmine/) 
with [js-imagediff](https://github.com/HumbleSoftware/js-imagediff) to test.  Tests may be executed by 
[jasmine-headless-webkit](http://johnbintz.github.com/jasmine-headless-webkit/) with 
`cd spec; jasmine-headless-webkit -j jasmine.yml -c` or by a browser by navigating to 
`flotr2/spec/SpecRunner.html`.

Shoutouts
---------

Thanks to Bas Wenneker, Fabien Ménager and others for all the work on the original Flotr.
Thanks to Jochen Berger and Jordan Santell for their contributions to Flotr2.

