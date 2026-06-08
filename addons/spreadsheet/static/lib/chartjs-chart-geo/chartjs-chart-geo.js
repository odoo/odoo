/**
 * chartjs-chart-geo
 * https://github.com/sgratzl/chartjs-chart-geo
 *
 * (c) 2019-2023 Samuel Gratzl <sam@sgratzl.com>
 * Released under the MIT license
 */

(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports, require('chart.js'), require('chart.js/helpers')) :
    typeof define === 'function' && define.amd ? define(['exports', 'chart.js', 'chart.js/helpers'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.ChartGeo = {}, global.Chart, global.Chart.helpers));
  })(this, (function (exports, chart_js, helpers) { 'use strict';

    // https://github.com/python/cpython/blob/a74eea238f5baba15797e2e8b570d153bc8690a7/Modules/mathmodule.c#L1423
    class Adder {
      constructor() {
        this._partials = new Float64Array(32);
        this._n = 0;
      }
      add(x) {
        const p = this._partials;
        let i = 0;
        for (let j = 0; j < this._n && j < 32; j++) {
          const y = p[j],
            hi = x + y,
            lo = Math.abs(x) < Math.abs(y) ? x - (hi - y) : y - (hi - x);
          if (lo) p[i++] = lo;
          x = hi;
        }
        p[i] = x;
        this._n = i + 1;
        return this;
      }
      valueOf() {
        const p = this._partials;
        let n = this._n, x, y, lo, hi = 0;
        if (n > 0) {
          hi = p[--n];
          while (n > 0) {
            x = hi;
            y = p[--n];
            hi = x + y;
            lo = y - (hi - x);
            if (lo) break;
          }
          if (n > 0 && ((lo < 0 && p[n - 1] < 0) || (lo > 0 && p[n - 1] > 0))) {
            y = lo * 2;
            x = hi + y;
            if (y == x - hi) hi = x;
          }
        }
        return hi;
      }
    }

    function* flatten(arrays) {
      for (const array of arrays) {
        yield* array;
      }
    }

    function merge$1(arrays) {
      return Array.from(flatten(arrays));
    }

    function range(start, stop, step) {
      start = +start, stop = +stop, step = (n = arguments.length) < 2 ? (stop = start, start = 0, 1) : n < 3 ? 1 : +step;

      var i = -1,
          n = Math.max(0, Math.ceil((stop - start) / step)) | 0,
          range = new Array(n);

      while (++i < n) {
        range[i] = start + i * step;
      }

      return range;
    }

    var epsilon = 1e-6;
    var epsilon2 = 1e-12;
    var pi = Math.PI;
    var halfPi = pi / 2;
    var quarterPi = pi / 4;
    var tau = pi * 2;

    var degrees$1 = 180 / pi;
    var radians$1 = pi / 180;

    var abs = Math.abs;
    var atan = Math.atan;
    var atan2 = Math.atan2;
    var cos = Math.cos;
    var ceil = Math.ceil;
    var exp = Math.exp;
    var log = Math.log;
    var pow = Math.pow;
    var sin = Math.sin;
    var sign = Math.sign || function(x) { return x > 0 ? 1 : x < 0 ? -1 : 0; };
    var sqrt = Math.sqrt;
    var tan = Math.tan;

    function acos(x) {
      return x > 1 ? 0 : x < -1 ? pi : Math.acos(x);
    }

    function asin(x) {
      return x > 1 ? halfPi : x < -1 ? -halfPi : Math.asin(x);
    }

    function noop() {}

    function streamGeometry(geometry, stream) {
      if (geometry && streamGeometryType.hasOwnProperty(geometry.type)) {
        streamGeometryType[geometry.type](geometry, stream);
      }
    }

    var streamObjectType = {
      Feature: function(object, stream) {
        streamGeometry(object.geometry, stream);
      },
      FeatureCollection: function(object, stream) {
        var features = object.features, i = -1, n = features.length;
        while (++i < n) streamGeometry(features[i].geometry, stream);
      }
    };

    var streamGeometryType = {
      Sphere: function(object, stream) {
        stream.sphere();
      },
      Point: function(object, stream) {
        object = object.coordinates;
        stream.point(object[0], object[1], object[2]);
      },
      MultiPoint: function(object, stream) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) object = coordinates[i], stream.point(object[0], object[1], object[2]);
      },
      LineString: function(object, stream) {
        streamLine(object.coordinates, stream, 0);
      },
      MultiLineString: function(object, stream) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) streamLine(coordinates[i], stream, 0);
      },
      Polygon: function(object, stream) {
        streamPolygon(object.coordinates, stream);
      },
      MultiPolygon: function(object, stream) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) streamPolygon(coordinates[i], stream);
      },
      GeometryCollection: function(object, stream) {
        var geometries = object.geometries, i = -1, n = geometries.length;
        while (++i < n) streamGeometry(geometries[i], stream);
      }
    };

    function streamLine(coordinates, stream, closed) {
      var i = -1, n = coordinates.length - closed, coordinate;
      stream.lineStart();
      while (++i < n) coordinate = coordinates[i], stream.point(coordinate[0], coordinate[1], coordinate[2]);
      stream.lineEnd();
    }

    function streamPolygon(coordinates, stream) {
      var i = -1, n = coordinates.length;
      stream.polygonStart();
      while (++i < n) streamLine(coordinates[i], stream, 1);
      stream.polygonEnd();
    }

    function geoStream(object, stream) {
      if (object && streamObjectType.hasOwnProperty(object.type)) {
        streamObjectType[object.type](object, stream);
      } else {
        streamGeometry(object, stream);
      }
    }

    function spherical(cartesian) {
      return [atan2(cartesian[1], cartesian[0]), asin(cartesian[2])];
    }

    function cartesian(spherical) {
      var lambda = spherical[0], phi = spherical[1], cosPhi = cos(phi);
      return [cosPhi * cos(lambda), cosPhi * sin(lambda), sin(phi)];
    }

    function cartesianDot(a, b) {
      return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    }

    function cartesianCross(a, b) {
      return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    }

    // TODO return a
    function cartesianAddInPlace(a, b) {
      a[0] += b[0], a[1] += b[1], a[2] += b[2];
    }

    function cartesianScale(vector, k) {
      return [vector[0] * k, vector[1] * k, vector[2] * k];
    }

    // TODO return d
    function cartesianNormalizeInPlace(d) {
      var l = sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
      d[0] /= l, d[1] /= l, d[2] /= l;
    }

    function compose(a, b) {

      function compose(x, y) {
        return x = a(x, y), b(x[0], x[1]);
      }

      if (a.invert && b.invert) compose.invert = function(x, y) {
        return x = b.invert(x, y), x && a.invert(x[0], x[1]);
      };

      return compose;
    }

    function rotationIdentity(lambda, phi) {
      if (abs(lambda) > pi) lambda -= Math.round(lambda / tau) * tau;
      return [lambda, phi];
    }

    rotationIdentity.invert = rotationIdentity;

    function rotateRadians(deltaLambda, deltaPhi, deltaGamma) {
      return (deltaLambda %= tau) ? (deltaPhi || deltaGamma ? compose(rotationLambda(deltaLambda), rotationPhiGamma(deltaPhi, deltaGamma))
        : rotationLambda(deltaLambda))
        : (deltaPhi || deltaGamma ? rotationPhiGamma(deltaPhi, deltaGamma)
        : rotationIdentity);
    }

    function forwardRotationLambda(deltaLambda) {
      return function(lambda, phi) {
        lambda += deltaLambda;
        if (abs(lambda) > pi) lambda -= Math.round(lambda / tau) * tau;
        return [lambda, phi];
      };
    }

    function rotationLambda(deltaLambda) {
      var rotation = forwardRotationLambda(deltaLambda);
      rotation.invert = forwardRotationLambda(-deltaLambda);
      return rotation;
    }

    function rotationPhiGamma(deltaPhi, deltaGamma) {
      var cosDeltaPhi = cos(deltaPhi),
          sinDeltaPhi = sin(deltaPhi),
          cosDeltaGamma = cos(deltaGamma),
          sinDeltaGamma = sin(deltaGamma);

      function rotation(lambda, phi) {
        var cosPhi = cos(phi),
            x = cos(lambda) * cosPhi,
            y = sin(lambda) * cosPhi,
            z = sin(phi),
            k = z * cosDeltaPhi + x * sinDeltaPhi;
        return [
          atan2(y * cosDeltaGamma - k * sinDeltaGamma, x * cosDeltaPhi - z * sinDeltaPhi),
          asin(k * cosDeltaGamma + y * sinDeltaGamma)
        ];
      }

      rotation.invert = function(lambda, phi) {
        var cosPhi = cos(phi),
            x = cos(lambda) * cosPhi,
            y = sin(lambda) * cosPhi,
            z = sin(phi),
            k = z * cosDeltaGamma - y * sinDeltaGamma;
        return [
          atan2(y * cosDeltaGamma + z * sinDeltaGamma, x * cosDeltaPhi + k * sinDeltaPhi),
          asin(k * cosDeltaPhi - x * sinDeltaPhi)
        ];
      };

      return rotation;
    }

    function rotation(rotate) {
      rotate = rotateRadians(rotate[0] * radians$1, rotate[1] * radians$1, rotate.length > 2 ? rotate[2] * radians$1 : 0);

      function forward(coordinates) {
        coordinates = rotate(coordinates[0] * radians$1, coordinates[1] * radians$1);
        return coordinates[0] *= degrees$1, coordinates[1] *= degrees$1, coordinates;
      }

      forward.invert = function(coordinates) {
        coordinates = rotate.invert(coordinates[0] * radians$1, coordinates[1] * radians$1);
        return coordinates[0] *= degrees$1, coordinates[1] *= degrees$1, coordinates;
      };

      return forward;
    }

    // Generates a circle centered at [0°, 0°], with a given radius and precision.
    function circleStream(stream, radius, delta, direction, t0, t1) {
      if (!delta) return;
      var cosRadius = cos(radius),
          sinRadius = sin(radius),
          step = direction * delta;
      if (t0 == null) {
        t0 = radius + direction * tau;
        t1 = radius - step / 2;
      } else {
        t0 = circleRadius(cosRadius, t0);
        t1 = circleRadius(cosRadius, t1);
        if (direction > 0 ? t0 < t1 : t0 > t1) t0 += direction * tau;
      }
      for (var point, t = t0; direction > 0 ? t > t1 : t < t1; t -= step) {
        point = spherical([cosRadius, -sinRadius * cos(t), -sinRadius * sin(t)]);
        stream.point(point[0], point[1]);
      }
    }

    // Returns the signed angle of a cartesian point relative to [cosRadius, 0, 0].
    function circleRadius(cosRadius, point) {
      point = cartesian(point), point[0] -= cosRadius;
      cartesianNormalizeInPlace(point);
      var radius = acos(-point[1]);
      return ((-point[2] < 0 ? -radius : radius) + tau - epsilon) % tau;
    }

    function clipBuffer() {
      var lines = [],
          line;
      return {
        point: function(x, y, m) {
          line.push([x, y, m]);
        },
        lineStart: function() {
          lines.push(line = []);
        },
        lineEnd: noop,
        rejoin: function() {
          if (lines.length > 1) lines.push(lines.pop().concat(lines.shift()));
        },
        result: function() {
          var result = lines;
          lines = [];
          line = null;
          return result;
        }
      };
    }

    function pointEqual(a, b) {
      return abs(a[0] - b[0]) < epsilon && abs(a[1] - b[1]) < epsilon;
    }

    function Intersection(point, points, other, entry) {
      this.x = point;
      this.z = points;
      this.o = other; // another intersection
      this.e = entry; // is an entry?
      this.v = false; // visited
      this.n = this.p = null; // next & previous
    }

    // A generalized polygon clipping algorithm: given a polygon that has been cut
    // into its visible line segments, and rejoins the segments by interpolating
    // along the clip edge.
    function clipRejoin(segments, compareIntersection, startInside, interpolate, stream) {
      var subject = [],
          clip = [],
          i,
          n;

      segments.forEach(function(segment) {
        if ((n = segment.length - 1) <= 0) return;
        var n, p0 = segment[0], p1 = segment[n], x;

        if (pointEqual(p0, p1)) {
          if (!p0[2] && !p1[2]) {
            stream.lineStart();
            for (i = 0; i < n; ++i) stream.point((p0 = segment[i])[0], p0[1]);
            stream.lineEnd();
            return;
          }
          // handle degenerate cases by moving the point
          p1[0] += 2 * epsilon;
        }

        subject.push(x = new Intersection(p0, segment, null, true));
        clip.push(x.o = new Intersection(p0, null, x, false));
        subject.push(x = new Intersection(p1, segment, null, false));
        clip.push(x.o = new Intersection(p1, null, x, true));
      });

      if (!subject.length) return;

      clip.sort(compareIntersection);
      link(subject);
      link(clip);

      for (i = 0, n = clip.length; i < n; ++i) {
        clip[i].e = startInside = !startInside;
      }

      var start = subject[0],
          points,
          point;

      while (1) {
        // Find first unvisited intersection.
        var current = start,
            isSubject = true;
        while (current.v) if ((current = current.n) === start) return;
        points = current.z;
        stream.lineStart();
        do {
          current.v = current.o.v = true;
          if (current.e) {
            if (isSubject) {
              for (i = 0, n = points.length; i < n; ++i) stream.point((point = points[i])[0], point[1]);
            } else {
              interpolate(current.x, current.n.x, 1, stream);
            }
            current = current.n;
          } else {
            if (isSubject) {
              points = current.p.z;
              for (i = points.length - 1; i >= 0; --i) stream.point((point = points[i])[0], point[1]);
            } else {
              interpolate(current.x, current.p.x, -1, stream);
            }
            current = current.p;
          }
          current = current.o;
          points = current.z;
          isSubject = !isSubject;
        } while (!current.v);
        stream.lineEnd();
      }
    }

    function link(array) {
      if (!(n = array.length)) return;
      var n,
          i = 0,
          a = array[0],
          b;
      while (++i < n) {
        a.n = b = array[i];
        b.p = a;
        a = b;
      }
      a.n = b = array[0];
      b.p = a;
    }

    function longitude(point) {
      return abs(point[0]) <= pi ? point[0] : sign(point[0]) * ((abs(point[0]) + pi) % tau - pi);
    }

    function polygonContains(polygon, point) {
      var lambda = longitude(point),
          phi = point[1],
          sinPhi = sin(phi),
          normal = [sin(lambda), -cos(lambda), 0],
          angle = 0,
          winding = 0;

      var sum = new Adder();

      if (sinPhi === 1) phi = halfPi + epsilon;
      else if (sinPhi === -1) phi = -halfPi - epsilon;

      for (var i = 0, n = polygon.length; i < n; ++i) {
        if (!(m = (ring = polygon[i]).length)) continue;
        var ring,
            m,
            point0 = ring[m - 1],
            lambda0 = longitude(point0),
            phi0 = point0[1] / 2 + quarterPi,
            sinPhi0 = sin(phi0),
            cosPhi0 = cos(phi0);

        for (var j = 0; j < m; ++j, lambda0 = lambda1, sinPhi0 = sinPhi1, cosPhi0 = cosPhi1, point0 = point1) {
          var point1 = ring[j],
              lambda1 = longitude(point1),
              phi1 = point1[1] / 2 + quarterPi,
              sinPhi1 = sin(phi1),
              cosPhi1 = cos(phi1),
              delta = lambda1 - lambda0,
              sign = delta >= 0 ? 1 : -1,
              absDelta = sign * delta,
              antimeridian = absDelta > pi,
              k = sinPhi0 * sinPhi1;

          sum.add(atan2(k * sign * sin(absDelta), cosPhi0 * cosPhi1 + k * cos(absDelta)));
          angle += antimeridian ? delta + sign * tau : delta;

          // Are the longitudes either side of the point’s meridian (lambda),
          // and are the latitudes smaller than the parallel (phi)?
          if (antimeridian ^ lambda0 >= lambda ^ lambda1 >= lambda) {
            var arc = cartesianCross(cartesian(point0), cartesian(point1));
            cartesianNormalizeInPlace(arc);
            var intersection = cartesianCross(normal, arc);
            cartesianNormalizeInPlace(intersection);
            var phiArc = (antimeridian ^ delta >= 0 ? -1 : 1) * asin(intersection[2]);
            if (phi > phiArc || phi === phiArc && (arc[0] || arc[1])) {
              winding += antimeridian ^ delta >= 0 ? 1 : -1;
            }
          }
        }
      }

      // First, determine whether the South pole is inside or outside:
      //
      // It is inside if:
      // * the polygon winds around it in a clockwise direction.
      // * the polygon does not (cumulatively) wind around it, but has a negative
      //   (counter-clockwise) area.
      //
      // Second, count the (signed) number of times a segment crosses a lambda
      // from the point to the South pole.  If it is zero, then the point is the
      // same side as the South pole.

      return (angle < -epsilon || angle < epsilon && sum < -epsilon2) ^ (winding & 1);
    }

    function clip(pointVisible, clipLine, interpolate, start) {
      return function(sink) {
        var line = clipLine(sink),
            ringBuffer = clipBuffer(),
            ringSink = clipLine(ringBuffer),
            polygonStarted = false,
            polygon,
            segments,
            ring;

        var clip = {
          point: point,
          lineStart: lineStart,
          lineEnd: lineEnd,
          polygonStart: function() {
            clip.point = pointRing;
            clip.lineStart = ringStart;
            clip.lineEnd = ringEnd;
            segments = [];
            polygon = [];
          },
          polygonEnd: function() {
            clip.point = point;
            clip.lineStart = lineStart;
            clip.lineEnd = lineEnd;
            segments = merge$1(segments);
            var startInside = polygonContains(polygon, start);
            if (segments.length) {
              if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
              clipRejoin(segments, compareIntersection, startInside, interpolate, sink);
            } else if (startInside) {
              if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
              sink.lineStart();
              interpolate(null, null, 1, sink);
              sink.lineEnd();
            }
            if (polygonStarted) sink.polygonEnd(), polygonStarted = false;
            segments = polygon = null;
          },
          sphere: function() {
            sink.polygonStart();
            sink.lineStart();
            interpolate(null, null, 1, sink);
            sink.lineEnd();
            sink.polygonEnd();
          }
        };

        function point(lambda, phi) {
          if (pointVisible(lambda, phi)) sink.point(lambda, phi);
        }

        function pointLine(lambda, phi) {
          line.point(lambda, phi);
        }

        function lineStart() {
          clip.point = pointLine;
          line.lineStart();
        }

        function lineEnd() {
          clip.point = point;
          line.lineEnd();
        }

        function pointRing(lambda, phi) {
          ring.push([lambda, phi]);
          ringSink.point(lambda, phi);
        }

        function ringStart() {
          ringSink.lineStart();
          ring = [];
        }

        function ringEnd() {
          pointRing(ring[0][0], ring[0][1]);
          ringSink.lineEnd();

          var clean = ringSink.clean(),
              ringSegments = ringBuffer.result(),
              i, n = ringSegments.length, m,
              segment,
              point;

          ring.pop();
          polygon.push(ring);
          ring = null;

          if (!n) return;

          // No intersections.
          if (clean & 1) {
            segment = ringSegments[0];
            if ((m = segment.length - 1) > 0) {
              if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
              sink.lineStart();
              for (i = 0; i < m; ++i) sink.point((point = segment[i])[0], point[1]);
              sink.lineEnd();
            }
            return;
          }

          // Rejoin connected segments.
          // TODO reuse ringBuffer.rejoin()?
          if (n > 1 && clean & 2) ringSegments.push(ringSegments.pop().concat(ringSegments.shift()));

          segments.push(ringSegments.filter(validSegment));
        }

        return clip;
      };
    }

    function validSegment(segment) {
      return segment.length > 1;
    }

    // Intersections are sorted along the clip edge. For both antimeridian cutting
    // and circle clipping, the same comparison is used.
    function compareIntersection(a, b) {
      return ((a = a.x)[0] < 0 ? a[1] - halfPi - epsilon : halfPi - a[1])
           - ((b = b.x)[0] < 0 ? b[1] - halfPi - epsilon : halfPi - b[1]);
    }

    var clipAntimeridian = clip(
      function() { return true; },
      clipAntimeridianLine,
      clipAntimeridianInterpolate,
      [-pi, -halfPi]
    );

    // Takes a line and cuts into visible segments. Return values: 0 - there were
    // intersections or the line was empty; 1 - no intersections; 2 - there were
    // intersections, and the first and last segments should be rejoined.
    function clipAntimeridianLine(stream) {
      var lambda0 = NaN,
          phi0 = NaN,
          sign0 = NaN,
          clean; // no intersections

      return {
        lineStart: function() {
          stream.lineStart();
          clean = 1;
        },
        point: function(lambda1, phi1) {
          var sign1 = lambda1 > 0 ? pi : -pi,
              delta = abs(lambda1 - lambda0);
          if (abs(delta - pi) < epsilon) { // line crosses a pole
            stream.point(lambda0, phi0 = (phi0 + phi1) / 2 > 0 ? halfPi : -halfPi);
            stream.point(sign0, phi0);
            stream.lineEnd();
            stream.lineStart();
            stream.point(sign1, phi0);
            stream.point(lambda1, phi0);
            clean = 0;
          } else if (sign0 !== sign1 && delta >= pi) { // line crosses antimeridian
            if (abs(lambda0 - sign0) < epsilon) lambda0 -= sign0 * epsilon; // handle degeneracies
            if (abs(lambda1 - sign1) < epsilon) lambda1 -= sign1 * epsilon;
            phi0 = clipAntimeridianIntersect(lambda0, phi0, lambda1, phi1);
            stream.point(sign0, phi0);
            stream.lineEnd();
            stream.lineStart();
            stream.point(sign1, phi0);
            clean = 0;
          }
          stream.point(lambda0 = lambda1, phi0 = phi1);
          sign0 = sign1;
        },
        lineEnd: function() {
          stream.lineEnd();
          lambda0 = phi0 = NaN;
        },
        clean: function() {
          return 2 - clean; // if intersections, rejoin first and last segments
        }
      };
    }

    function clipAntimeridianIntersect(lambda0, phi0, lambda1, phi1) {
      var cosPhi0,
          cosPhi1,
          sinLambda0Lambda1 = sin(lambda0 - lambda1);
      return abs(sinLambda0Lambda1) > epsilon
          ? atan((sin(phi0) * (cosPhi1 = cos(phi1)) * sin(lambda1)
              - sin(phi1) * (cosPhi0 = cos(phi0)) * sin(lambda0))
              / (cosPhi0 * cosPhi1 * sinLambda0Lambda1))
          : (phi0 + phi1) / 2;
    }

    function clipAntimeridianInterpolate(from, to, direction, stream) {
      var phi;
      if (from == null) {
        phi = direction * halfPi;
        stream.point(-pi, phi);
        stream.point(0, phi);
        stream.point(pi, phi);
        stream.point(pi, 0);
        stream.point(pi, -phi);
        stream.point(0, -phi);
        stream.point(-pi, -phi);
        stream.point(-pi, 0);
        stream.point(-pi, phi);
      } else if (abs(from[0] - to[0]) > epsilon) {
        var lambda = from[0] < to[0] ? pi : -pi;
        phi = direction * lambda / 2;
        stream.point(-lambda, phi);
        stream.point(0, phi);
        stream.point(lambda, phi);
      } else {
        stream.point(to[0], to[1]);
      }
    }

    function clipCircle(radius) {
      var cr = cos(radius),
          delta = 2 * radians$1,
          smallRadius = cr > 0,
          notHemisphere = abs(cr) > epsilon; // TODO optimise for this common case

      function interpolate(from, to, direction, stream) {
        circleStream(stream, radius, delta, direction, from, to);
      }

      function visible(lambda, phi) {
        return cos(lambda) * cos(phi) > cr;
      }

      // Takes a line and cuts into visible segments. Return values used for polygon
      // clipping: 0 - there were intersections or the line was empty; 1 - no
      // intersections 2 - there were intersections, and the first and last segments
      // should be rejoined.
      function clipLine(stream) {
        var point0, // previous point
            c0, // code for previous point
            v0, // visibility of previous point
            v00, // visibility of first point
            clean; // no intersections
        return {
          lineStart: function() {
            v00 = v0 = false;
            clean = 1;
          },
          point: function(lambda, phi) {
            var point1 = [lambda, phi],
                point2,
                v = visible(lambda, phi),
                c = smallRadius
                  ? v ? 0 : code(lambda, phi)
                  : v ? code(lambda + (lambda < 0 ? pi : -pi), phi) : 0;
            if (!point0 && (v00 = v0 = v)) stream.lineStart();
            if (v !== v0) {
              point2 = intersect(point0, point1);
              if (!point2 || pointEqual(point0, point2) || pointEqual(point1, point2))
                point1[2] = 1;
            }
            if (v !== v0) {
              clean = 0;
              if (v) {
                // outside going in
                stream.lineStart();
                point2 = intersect(point1, point0);
                stream.point(point2[0], point2[1]);
              } else {
                // inside going out
                point2 = intersect(point0, point1);
                stream.point(point2[0], point2[1], 2);
                stream.lineEnd();
              }
              point0 = point2;
            } else if (notHemisphere && point0 && smallRadius ^ v) {
              var t;
              // If the codes for two points are different, or are both zero,
              // and there this segment intersects with the small circle.
              if (!(c & c0) && (t = intersect(point1, point0, true))) {
                clean = 0;
                if (smallRadius) {
                  stream.lineStart();
                  stream.point(t[0][0], t[0][1]);
                  stream.point(t[1][0], t[1][1]);
                  stream.lineEnd();
                } else {
                  stream.point(t[1][0], t[1][1]);
                  stream.lineEnd();
                  stream.lineStart();
                  stream.point(t[0][0], t[0][1], 3);
                }
              }
            }
            if (v && (!point0 || !pointEqual(point0, point1))) {
              stream.point(point1[0], point1[1]);
            }
            point0 = point1, v0 = v, c0 = c;
          },
          lineEnd: function() {
            if (v0) stream.lineEnd();
            point0 = null;
          },
          // Rejoin first and last segments if there were intersections and the first
          // and last points were visible.
          clean: function() {
            return clean | ((v00 && v0) << 1);
          }
        };
      }

      // Intersects the great circle between a and b with the clip circle.
      function intersect(a, b, two) {
        var pa = cartesian(a),
            pb = cartesian(b);

        // We have two planes, n1.p = d1 and n2.p = d2.
        // Find intersection line p(t) = c1 n1 + c2 n2 + t (n1 ⨯ n2).
        var n1 = [1, 0, 0], // normal
            n2 = cartesianCross(pa, pb),
            n2n2 = cartesianDot(n2, n2),
            n1n2 = n2[0], // cartesianDot(n1, n2),
            determinant = n2n2 - n1n2 * n1n2;

        // Two polar points.
        if (!determinant) return !two && a;

        var c1 =  cr * n2n2 / determinant,
            c2 = -cr * n1n2 / determinant,
            n1xn2 = cartesianCross(n1, n2),
            A = cartesianScale(n1, c1),
            B = cartesianScale(n2, c2);
        cartesianAddInPlace(A, B);

        // Solve |p(t)|^2 = 1.
        var u = n1xn2,
            w = cartesianDot(A, u),
            uu = cartesianDot(u, u),
            t2 = w * w - uu * (cartesianDot(A, A) - 1);

        if (t2 < 0) return;

        var t = sqrt(t2),
            q = cartesianScale(u, (-w - t) / uu);
        cartesianAddInPlace(q, A);
        q = spherical(q);

        if (!two) return q;

        // Two intersection points.
        var lambda0 = a[0],
            lambda1 = b[0],
            phi0 = a[1],
            phi1 = b[1],
            z;

        if (lambda1 < lambda0) z = lambda0, lambda0 = lambda1, lambda1 = z;

        var delta = lambda1 - lambda0,
            polar = abs(delta - pi) < epsilon,
            meridian = polar || delta < epsilon;

        if (!polar && phi1 < phi0) z = phi0, phi0 = phi1, phi1 = z;

        // Check that the first point is between a and b.
        if (meridian
            ? polar
              ? phi0 + phi1 > 0 ^ q[1] < (abs(q[0] - lambda0) < epsilon ? phi0 : phi1)
              : phi0 <= q[1] && q[1] <= phi1
            : delta > pi ^ (lambda0 <= q[0] && q[0] <= lambda1)) {
          var q1 = cartesianScale(u, (-w + t) / uu);
          cartesianAddInPlace(q1, A);
          return [q, spherical(q1)];
        }
      }

      // Generates a 4-bit vector representing the location of a point relative to
      // the small circle's bounding box.
      function code(lambda, phi) {
        var r = smallRadius ? radius : pi - radius,
            code = 0;
        if (lambda < -r) code |= 1; // left
        else if (lambda > r) code |= 2; // right
        if (phi < -r) code |= 4; // below
        else if (phi > r) code |= 8; // above
        return code;
      }

      return clip(visible, clipLine, interpolate, smallRadius ? [0, -radius] : [-pi, radius - pi]);
    }

    function clipLine(a, b, x0, y0, x1, y1) {
      var ax = a[0],
          ay = a[1],
          bx = b[0],
          by = b[1],
          t0 = 0,
          t1 = 1,
          dx = bx - ax,
          dy = by - ay,
          r;

      r = x0 - ax;
      if (!dx && r > 0) return;
      r /= dx;
      if (dx < 0) {
        if (r < t0) return;
        if (r < t1) t1 = r;
      } else if (dx > 0) {
        if (r > t1) return;
        if (r > t0) t0 = r;
      }

      r = x1 - ax;
      if (!dx && r < 0) return;
      r /= dx;
      if (dx < 0) {
        if (r > t1) return;
        if (r > t0) t0 = r;
      } else if (dx > 0) {
        if (r < t0) return;
        if (r < t1) t1 = r;
      }

      r = y0 - ay;
      if (!dy && r > 0) return;
      r /= dy;
      if (dy < 0) {
        if (r < t0) return;
        if (r < t1) t1 = r;
      } else if (dy > 0) {
        if (r > t1) return;
        if (r > t0) t0 = r;
      }

      r = y1 - ay;
      if (!dy && r < 0) return;
      r /= dy;
      if (dy < 0) {
        if (r > t1) return;
        if (r > t0) t0 = r;
      } else if (dy > 0) {
        if (r < t0) return;
        if (r < t1) t1 = r;
      }

      if (t0 > 0) a[0] = ax + t0 * dx, a[1] = ay + t0 * dy;
      if (t1 < 1) b[0] = ax + t1 * dx, b[1] = ay + t1 * dy;
      return true;
    }

    var clipMax = 1e9, clipMin = -clipMax;

    // TODO Use d3-polygon’s polygonContains here for the ring check?
    // TODO Eliminate duplicate buffering in clipBuffer and polygon.push?

    function clipRectangle(x0, y0, x1, y1) {

      function visible(x, y) {
        return x0 <= x && x <= x1 && y0 <= y && y <= y1;
      }

      function interpolate(from, to, direction, stream) {
        var a = 0, a1 = 0;
        if (from == null
            || (a = corner(from, direction)) !== (a1 = corner(to, direction))
            || comparePoint(from, to) < 0 ^ direction > 0) {
          do stream.point(a === 0 || a === 3 ? x0 : x1, a > 1 ? y1 : y0);
          while ((a = (a + direction + 4) % 4) !== a1);
        } else {
          stream.point(to[0], to[1]);
        }
      }

      function corner(p, direction) {
        return abs(p[0] - x0) < epsilon ? direction > 0 ? 0 : 3
            : abs(p[0] - x1) < epsilon ? direction > 0 ? 2 : 1
            : abs(p[1] - y0) < epsilon ? direction > 0 ? 1 : 0
            : direction > 0 ? 3 : 2; // abs(p[1] - y1) < epsilon
      }

      function compareIntersection(a, b) {
        return comparePoint(a.x, b.x);
      }

      function comparePoint(a, b) {
        var ca = corner(a, 1),
            cb = corner(b, 1);
        return ca !== cb ? ca - cb
            : ca === 0 ? b[1] - a[1]
            : ca === 1 ? a[0] - b[0]
            : ca === 2 ? a[1] - b[1]
            : b[0] - a[0];
      }

      return function(stream) {
        var activeStream = stream,
            bufferStream = clipBuffer(),
            segments,
            polygon,
            ring,
            x__, y__, v__, // first point
            x_, y_, v_, // previous point
            first,
            clean;

        var clipStream = {
          point: point,
          lineStart: lineStart,
          lineEnd: lineEnd,
          polygonStart: polygonStart,
          polygonEnd: polygonEnd
        };

        function point(x, y) {
          if (visible(x, y)) activeStream.point(x, y);
        }

        function polygonInside() {
          var winding = 0;

          for (var i = 0, n = polygon.length; i < n; ++i) {
            for (var ring = polygon[i], j = 1, m = ring.length, point = ring[0], a0, a1, b0 = point[0], b1 = point[1]; j < m; ++j) {
              a0 = b0, a1 = b1, point = ring[j], b0 = point[0], b1 = point[1];
              if (a1 <= y1) { if (b1 > y1 && (b0 - a0) * (y1 - a1) > (b1 - a1) * (x0 - a0)) ++winding; }
              else { if (b1 <= y1 && (b0 - a0) * (y1 - a1) < (b1 - a1) * (x0 - a0)) --winding; }
            }
          }

          return winding;
        }

        // Buffer geometry within a polygon and then clip it en masse.
        function polygonStart() {
          activeStream = bufferStream, segments = [], polygon = [], clean = true;
        }

        function polygonEnd() {
          var startInside = polygonInside(),
              cleanInside = clean && startInside,
              visible = (segments = merge$1(segments)).length;
          if (cleanInside || visible) {
            stream.polygonStart();
            if (cleanInside) {
              stream.lineStart();
              interpolate(null, null, 1, stream);
              stream.lineEnd();
            }
            if (visible) {
              clipRejoin(segments, compareIntersection, startInside, interpolate, stream);
            }
            stream.polygonEnd();
          }
          activeStream = stream, segments = polygon = ring = null;
        }

        function lineStart() {
          clipStream.point = linePoint;
          if (polygon) polygon.push(ring = []);
          first = true;
          v_ = false;
          x_ = y_ = NaN;
        }

        // TODO rather than special-case polygons, simply handle them separately.
        // Ideally, coincident intersection points should be jittered to avoid
        // clipping issues.
        function lineEnd() {
          if (segments) {
            linePoint(x__, y__);
            if (v__ && v_) bufferStream.rejoin();
            segments.push(bufferStream.result());
          }
          clipStream.point = point;
          if (v_) activeStream.lineEnd();
        }

        function linePoint(x, y) {
          var v = visible(x, y);
          if (polygon) ring.push([x, y]);
          if (first) {
            x__ = x, y__ = y, v__ = v;
            first = false;
            if (v) {
              activeStream.lineStart();
              activeStream.point(x, y);
            }
          } else {
            if (v && v_) activeStream.point(x, y);
            else {
              var a = [x_ = Math.max(clipMin, Math.min(clipMax, x_)), y_ = Math.max(clipMin, Math.min(clipMax, y_))],
                  b = [x = Math.max(clipMin, Math.min(clipMax, x)), y = Math.max(clipMin, Math.min(clipMax, y))];
              if (clipLine(a, b, x0, y0, x1, y1)) {
                if (!v_) {
                  activeStream.lineStart();
                  activeStream.point(a[0], a[1]);
                }
                activeStream.point(b[0], b[1]);
                if (!v) activeStream.lineEnd();
                clean = false;
              } else if (v) {
                activeStream.lineStart();
                activeStream.point(x, y);
                clean = false;
              }
            }
          }
          x_ = x, y_ = y, v_ = v;
        }

        return clipStream;
      };
    }

    var lengthSum$1,
        lambda0,
        sinPhi0,
        cosPhi0;

    var lengthStream$1 = {
      sphere: noop,
      point: noop,
      lineStart: lengthLineStart,
      lineEnd: noop,
      polygonStart: noop,
      polygonEnd: noop
    };

    function lengthLineStart() {
      lengthStream$1.point = lengthPointFirst$1;
      lengthStream$1.lineEnd = lengthLineEnd;
    }

    function lengthLineEnd() {
      lengthStream$1.point = lengthStream$1.lineEnd = noop;
    }

    function lengthPointFirst$1(lambda, phi) {
      lambda *= radians$1, phi *= radians$1;
      lambda0 = lambda, sinPhi0 = sin(phi), cosPhi0 = cos(phi);
      lengthStream$1.point = lengthPoint$1;
    }

    function lengthPoint$1(lambda, phi) {
      lambda *= radians$1, phi *= radians$1;
      var sinPhi = sin(phi),
          cosPhi = cos(phi),
          delta = abs(lambda - lambda0),
          cosDelta = cos(delta),
          sinDelta = sin(delta),
          x = cosPhi * sinDelta,
          y = cosPhi0 * sinPhi - sinPhi0 * cosPhi * cosDelta,
          z = sinPhi0 * sinPhi + cosPhi0 * cosPhi * cosDelta;
      lengthSum$1.add(atan2(sqrt(x * x + y * y), z));
      lambda0 = lambda, sinPhi0 = sinPhi, cosPhi0 = cosPhi;
    }

    function length(object) {
      lengthSum$1 = new Adder();
      geoStream(object, lengthStream$1);
      return +lengthSum$1;
    }

    var coordinates = [null, null],
        object$1 = {type: "LineString", coordinates: coordinates};

    function distance(a, b) {
      coordinates[0] = a;
      coordinates[1] = b;
      return length(object$1);
    }

    var containsObjectType = {
      Feature: function(object, point) {
        return containsGeometry(object.geometry, point);
      },
      FeatureCollection: function(object, point) {
        var features = object.features, i = -1, n = features.length;
        while (++i < n) if (containsGeometry(features[i].geometry, point)) return true;
        return false;
      }
    };

    var containsGeometryType = {
      Sphere: function() {
        return true;
      },
      Point: function(object, point) {
        return containsPoint(object.coordinates, point);
      },
      MultiPoint: function(object, point) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) if (containsPoint(coordinates[i], point)) return true;
        return false;
      },
      LineString: function(object, point) {
        return containsLine(object.coordinates, point);
      },
      MultiLineString: function(object, point) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) if (containsLine(coordinates[i], point)) return true;
        return false;
      },
      Polygon: function(object, point) {
        return containsPolygon(object.coordinates, point);
      },
      MultiPolygon: function(object, point) {
        var coordinates = object.coordinates, i = -1, n = coordinates.length;
        while (++i < n) if (containsPolygon(coordinates[i], point)) return true;
        return false;
      },
      GeometryCollection: function(object, point) {
        var geometries = object.geometries, i = -1, n = geometries.length;
        while (++i < n) if (containsGeometry(geometries[i], point)) return true;
        return false;
      }
    };

    function containsGeometry(geometry, point) {
      return geometry && containsGeometryType.hasOwnProperty(geometry.type)
          ? containsGeometryType[geometry.type](geometry, point)
          : false;
    }

    function containsPoint(coordinates, point) {
      return distance(coordinates, point) === 0;
    }

    function containsLine(coordinates, point) {
      var ao, bo, ab;
      for (var i = 0, n = coordinates.length; i < n; i++) {
        bo = distance(coordinates[i], point);
        if (bo === 0) return true;
        if (i > 0) {
          ab = distance(coordinates[i], coordinates[i - 1]);
          if (
            ab > 0 &&
            ao <= ab &&
            bo <= ab &&
            (ao + bo - ab) * (1 - Math.pow((ao - bo) / ab, 2)) < epsilon2 * ab
          )
            return true;
        }
        ao = bo;
      }
      return false;
    }

    function containsPolygon(coordinates, point) {
      return !!polygonContains(coordinates.map(ringRadians), pointRadians(point));
    }

    function ringRadians(ring) {
      return ring = ring.map(pointRadians), ring.pop(), ring;
    }

    function pointRadians(point) {
      return [point[0] * radians$1, point[1] * radians$1];
    }

    function geoContains(object, point) {
      return (object && containsObjectType.hasOwnProperty(object.type)
          ? containsObjectType[object.type]
          : containsGeometry)(object, point);
    }

    function graticuleX(y0, y1, dy) {
      var y = range(y0, y1 - epsilon, dy).concat(y1);
      return function(x) { return y.map(function(y) { return [x, y]; }); };
    }

    function graticuleY(x0, x1, dx) {
      var x = range(x0, x1 - epsilon, dx).concat(x1);
      return function(y) { return x.map(function(x) { return [x, y]; }); };
    }

    function graticule() {
      var x1, x0, X1, X0,
          y1, y0, Y1, Y0,
          dx = 10, dy = dx, DX = 90, DY = 360,
          x, y, X, Y,
          precision = 2.5;

      function graticule() {
        return {type: "MultiLineString", coordinates: lines()};
      }

      function lines() {
        return range(ceil(X0 / DX) * DX, X1, DX).map(X)
            .concat(range(ceil(Y0 / DY) * DY, Y1, DY).map(Y))
            .concat(range(ceil(x0 / dx) * dx, x1, dx).filter(function(x) { return abs(x % DX) > epsilon; }).map(x))
            .concat(range(ceil(y0 / dy) * dy, y1, dy).filter(function(y) { return abs(y % DY) > epsilon; }).map(y));
      }

      graticule.lines = function() {
        return lines().map(function(coordinates) { return {type: "LineString", coordinates: coordinates}; });
      };

      graticule.outline = function() {
        return {
          type: "Polygon",
          coordinates: [
            X(X0).concat(
            Y(Y1).slice(1),
            X(X1).reverse().slice(1),
            Y(Y0).reverse().slice(1))
          ]
        };
      };

      graticule.extent = function(_) {
        if (!arguments.length) return graticule.extentMinor();
        return graticule.extentMajor(_).extentMinor(_);
      };

      graticule.extentMajor = function(_) {
        if (!arguments.length) return [[X0, Y0], [X1, Y1]];
        X0 = +_[0][0], X1 = +_[1][0];
        Y0 = +_[0][1], Y1 = +_[1][1];
        if (X0 > X1) _ = X0, X0 = X1, X1 = _;
        if (Y0 > Y1) _ = Y0, Y0 = Y1, Y1 = _;
        return graticule.precision(precision);
      };

      graticule.extentMinor = function(_) {
        if (!arguments.length) return [[x0, y0], [x1, y1]];
        x0 = +_[0][0], x1 = +_[1][0];
        y0 = +_[0][1], y1 = +_[1][1];
        if (x0 > x1) _ = x0, x0 = x1, x1 = _;
        if (y0 > y1) _ = y0, y0 = y1, y1 = _;
        return graticule.precision(precision);
      };

      graticule.step = function(_) {
        if (!arguments.length) return graticule.stepMinor();
        return graticule.stepMajor(_).stepMinor(_);
      };

      graticule.stepMajor = function(_) {
        if (!arguments.length) return [DX, DY];
        DX = +_[0], DY = +_[1];
        return graticule;
      };

      graticule.stepMinor = function(_) {
        if (!arguments.length) return [dx, dy];
        dx = +_[0], dy = +_[1];
        return graticule;
      };

      graticule.precision = function(_) {
        if (!arguments.length) return precision;
        precision = +_;
        x = graticuleX(y0, y1, 90);
        y = graticuleY(x0, x1, precision);
        X = graticuleX(Y0, Y1, 90);
        Y = graticuleY(X0, X1, precision);
        return graticule;
      };

      return graticule
          .extentMajor([[-180, -90 + epsilon], [180, 90 - epsilon]])
          .extentMinor([[-180, -80 - epsilon], [180, 80 + epsilon]]);
    }

    function graticule10() {
      return graticule()();
    }

    var identity$1 = x => x;

    var areaSum = new Adder(),
        areaRingSum = new Adder(),
        x00$2,
        y00$2,
        x0$3,
        y0$3;

    var areaStream = {
      point: noop,
      lineStart: noop,
      lineEnd: noop,
      polygonStart: function() {
        areaStream.lineStart = areaRingStart;
        areaStream.lineEnd = areaRingEnd;
      },
      polygonEnd: function() {
        areaStream.lineStart = areaStream.lineEnd = areaStream.point = noop;
        areaSum.add(abs(areaRingSum));
        areaRingSum = new Adder();
      },
      result: function() {
        var area = areaSum / 2;
        areaSum = new Adder();
        return area;
      }
    };

    function areaRingStart() {
      areaStream.point = areaPointFirst;
    }

    function areaPointFirst(x, y) {
      areaStream.point = areaPoint;
      x00$2 = x0$3 = x, y00$2 = y0$3 = y;
    }

    function areaPoint(x, y) {
      areaRingSum.add(y0$3 * x - x0$3 * y);
      x0$3 = x, y0$3 = y;
    }

    function areaRingEnd() {
      areaPoint(x00$2, y00$2);
    }

    var x0$2 = Infinity,
        y0$2 = x0$2,
        x1 = -x0$2,
        y1 = x1;

    var boundsStream = {
      point: boundsPoint,
      lineStart: noop,
      lineEnd: noop,
      polygonStart: noop,
      polygonEnd: noop,
      result: function() {
        var bounds = [[x0$2, y0$2], [x1, y1]];
        x1 = y1 = -(y0$2 = x0$2 = Infinity);
        return bounds;
      }
    };

    function boundsPoint(x, y) {
      if (x < x0$2) x0$2 = x;
      if (x > x1) x1 = x;
      if (y < y0$2) y0$2 = y;
      if (y > y1) y1 = y;
    }

    // TODO Enforce positive area for exterior, negative area for interior?

    var X0 = 0,
        Y0 = 0,
        Z0 = 0,
        X1 = 0,
        Y1 = 0,
        Z1 = 0,
        X2 = 0,
        Y2 = 0,
        Z2 = 0,
        x00$1,
        y00$1,
        x0$1,
        y0$1;

    var centroidStream = {
      point: centroidPoint,
      lineStart: centroidLineStart,
      lineEnd: centroidLineEnd,
      polygonStart: function() {
        centroidStream.lineStart = centroidRingStart;
        centroidStream.lineEnd = centroidRingEnd;
      },
      polygonEnd: function() {
        centroidStream.point = centroidPoint;
        centroidStream.lineStart = centroidLineStart;
        centroidStream.lineEnd = centroidLineEnd;
      },
      result: function() {
        var centroid = Z2 ? [X2 / Z2, Y2 / Z2]
            : Z1 ? [X1 / Z1, Y1 / Z1]
            : Z0 ? [X0 / Z0, Y0 / Z0]
            : [NaN, NaN];
        X0 = Y0 = Z0 =
        X1 = Y1 = Z1 =
        X2 = Y2 = Z2 = 0;
        return centroid;
      }
    };

    function centroidPoint(x, y) {
      X0 += x;
      Y0 += y;
      ++Z0;
    }

    function centroidLineStart() {
      centroidStream.point = centroidPointFirstLine;
    }

    function centroidPointFirstLine(x, y) {
      centroidStream.point = centroidPointLine;
      centroidPoint(x0$1 = x, y0$1 = y);
    }

    function centroidPointLine(x, y) {
      var dx = x - x0$1, dy = y - y0$1, z = sqrt(dx * dx + dy * dy);
      X1 += z * (x0$1 + x) / 2;
      Y1 += z * (y0$1 + y) / 2;
      Z1 += z;
      centroidPoint(x0$1 = x, y0$1 = y);
    }

    function centroidLineEnd() {
      centroidStream.point = centroidPoint;
    }

    function centroidRingStart() {
      centroidStream.point = centroidPointFirstRing;
    }

    function centroidRingEnd() {
      centroidPointRing(x00$1, y00$1);
    }

    function centroidPointFirstRing(x, y) {
      centroidStream.point = centroidPointRing;
      centroidPoint(x00$1 = x0$1 = x, y00$1 = y0$1 = y);
    }

    function centroidPointRing(x, y) {
      var dx = x - x0$1,
          dy = y - y0$1,
          z = sqrt(dx * dx + dy * dy);

      X1 += z * (x0$1 + x) / 2;
      Y1 += z * (y0$1 + y) / 2;
      Z1 += z;

      z = y0$1 * x - x0$1 * y;
      X2 += z * (x0$1 + x);
      Y2 += z * (y0$1 + y);
      Z2 += z * 3;
      centroidPoint(x0$1 = x, y0$1 = y);
    }

    function PathContext(context) {
      this._context = context;
    }

    PathContext.prototype = {
      _radius: 4.5,
      pointRadius: function(_) {
        return this._radius = _, this;
      },
      polygonStart: function() {
        this._line = 0;
      },
      polygonEnd: function() {
        this._line = NaN;
      },
      lineStart: function() {
        this._point = 0;
      },
      lineEnd: function() {
        if (this._line === 0) this._context.closePath();
        this._point = NaN;
      },
      point: function(x, y) {
        switch (this._point) {
          case 0: {
            this._context.moveTo(x, y);
            this._point = 1;
            break;
          }
          case 1: {
            this._context.lineTo(x, y);
            break;
          }
          default: {
            this._context.moveTo(x + this._radius, y);
            this._context.arc(x, y, this._radius, 0, tau);
            break;
          }
        }
      },
      result: noop
    };

    var lengthSum = new Adder(),
        lengthRing,
        x00,
        y00,
        x0,
        y0;

    var lengthStream = {
      point: noop,
      lineStart: function() {
        lengthStream.point = lengthPointFirst;
      },
      lineEnd: function() {
        if (lengthRing) lengthPoint(x00, y00);
        lengthStream.point = noop;
      },
      polygonStart: function() {
        lengthRing = true;
      },
      polygonEnd: function() {
        lengthRing = null;
      },
      result: function() {
        var length = +lengthSum;
        lengthSum = new Adder();
        return length;
      }
    };

    function lengthPointFirst(x, y) {
      lengthStream.point = lengthPoint;
      x00 = x0 = x, y00 = y0 = y;
    }

    function lengthPoint(x, y) {
      x0 -= x, y0 -= y;
      lengthSum.add(sqrt(x0 * x0 + y0 * y0));
      x0 = x, y0 = y;
    }

    // Simple caching for constant-radius points.
    let cacheDigits, cacheAppend, cacheRadius, cacheCircle;

    class PathString {
      constructor(digits) {
        this._append = digits == null ? append : appendRound(digits);
        this._radius = 4.5;
        this._ = "";
      }
      pointRadius(_) {
        this._radius = +_;
        return this;
      }
      polygonStart() {
        this._line = 0;
      }
      polygonEnd() {
        this._line = NaN;
      }
      lineStart() {
        this._point = 0;
      }
      lineEnd() {
        if (this._line === 0) this._ += "Z";
        this._point = NaN;
      }
      point(x, y) {
        switch (this._point) {
          case 0: {
            this._append`M${x},${y}`;
            this._point = 1;
            break;
          }
          case 1: {
            this._append`L${x},${y}`;
            break;
          }
          default: {
            this._append`M${x},${y}`;
            if (this._radius !== cacheRadius || this._append !== cacheAppend) {
              const r = this._radius;
              const s = this._;
              this._ = ""; // stash the old string so we can cache the circle path fragment
              this._append`m0,${r}a${r},${r} 0 1,1 0,${-2 * r}a${r},${r} 0 1,1 0,${2 * r}z`;
              cacheRadius = r;
              cacheAppend = this._append;
              cacheCircle = this._;
              this._ = s;
            }
            this._ += cacheCircle;
            break;
          }
        }
      }
      result() {
        const result = this._;
        this._ = "";
        return result.length ? result : null;
      }
    }

    function append(strings) {
      let i = 1;
      this._ += strings[0];
      for (const j = strings.length; i < j; ++i) {
        this._ += arguments[i] + strings[i];
      }
    }

    function appendRound(digits) {
      const d = Math.floor(digits);
      if (!(d >= 0)) throw new RangeError(`invalid digits: ${digits}`);
      if (d > 15) return append;
      if (d !== cacheDigits) {
        const k = 10 ** d;
        cacheDigits = d;
        cacheAppend = function append(strings) {
          let i = 1;
          this._ += strings[0];
          for (const j = strings.length; i < j; ++i) {
            this._ += Math.round(arguments[i] * k) / k + strings[i];
          }
        };
      }
      return cacheAppend;
    }

    function geoPath(projection, context) {
      let digits = 3,
          pointRadius = 4.5,
          projectionStream,
          contextStream;

      function path(object) {
        if (object) {
          if (typeof pointRadius === "function") contextStream.pointRadius(+pointRadius.apply(this, arguments));
          geoStream(object, projectionStream(contextStream));
        }
        return contextStream.result();
      }

      path.area = function(object) {
        geoStream(object, projectionStream(areaStream));
        return areaStream.result();
      };

      path.measure = function(object) {
        geoStream(object, projectionStream(lengthStream));
        return lengthStream.result();
      };

      path.bounds = function(object) {
        geoStream(object, projectionStream(boundsStream));
        return boundsStream.result();
      };

      path.centroid = function(object) {
        geoStream(object, projectionStream(centroidStream));
        return centroidStream.result();
      };

      path.projection = function(_) {
        if (!arguments.length) return projection;
        projectionStream = _ == null ? (projection = null, identity$1) : (projection = _).stream;
        return path;
      };

      path.context = function(_) {
        if (!arguments.length) return context;
        contextStream = _ == null ? (context = null, new PathString(digits)) : new PathContext(context = _);
        if (typeof pointRadius !== "function") contextStream.pointRadius(pointRadius);
        return path;
      };

      path.pointRadius = function(_) {
        if (!arguments.length) return pointRadius;
        pointRadius = typeof _ === "function" ? _ : (contextStream.pointRadius(+_), +_);
        return path;
      };

      path.digits = function(_) {
        if (!arguments.length) return digits;
        if (_ == null) digits = null;
        else {
          const d = Math.floor(_);
          if (!(d >= 0)) throw new RangeError(`invalid digits: ${_}`);
          digits = d;
        }
        if (context === null) contextStream = new PathString(digits);
        return path;
      };

      return path.projection(projection).digits(digits).context(context);
    }

    function transformer(methods) {
      return function(stream) {
        var s = new TransformStream;
        for (var key in methods) s[key] = methods[key];
        s.stream = stream;
        return s;
      };
    }

    function TransformStream() {}

    TransformStream.prototype = {
      constructor: TransformStream,
      point: function(x, y) { this.stream.point(x, y); },
      sphere: function() { this.stream.sphere(); },
      lineStart: function() { this.stream.lineStart(); },
      lineEnd: function() { this.stream.lineEnd(); },
      polygonStart: function() { this.stream.polygonStart(); },
      polygonEnd: function() { this.stream.polygonEnd(); }
    };

    function fit(projection, fitBounds, object) {
      var clip = projection.clipExtent && projection.clipExtent();
      projection.scale(150).translate([0, 0]);
      if (clip != null) projection.clipExtent(null);
      geoStream(object, projection.stream(boundsStream));
      fitBounds(boundsStream.result());
      if (clip != null) projection.clipExtent(clip);
      return projection;
    }

    function fitExtent(projection, extent, object) {
      return fit(projection, function(b) {
        var w = extent[1][0] - extent[0][0],
            h = extent[1][1] - extent[0][1],
            k = Math.min(w / (b[1][0] - b[0][0]), h / (b[1][1] - b[0][1])),
            x = +extent[0][0] + (w - k * (b[1][0] + b[0][0])) / 2,
            y = +extent[0][1] + (h - k * (b[1][1] + b[0][1])) / 2;
        projection.scale(150 * k).translate([x, y]);
      }, object);
    }

    function fitSize(projection, size, object) {
      return fitExtent(projection, [[0, 0], size], object);
    }

    function fitWidth(projection, width, object) {
      return fit(projection, function(b) {
        var w = +width,
            k = w / (b[1][0] - b[0][0]),
            x = (w - k * (b[1][0] + b[0][0])) / 2,
            y = -k * b[0][1];
        projection.scale(150 * k).translate([x, y]);
      }, object);
    }

    function fitHeight(projection, height, object) {
      return fit(projection, function(b) {
        var h = +height,
            k = h / (b[1][1] - b[0][1]),
            x = -k * b[0][0],
            y = (h - k * (b[1][1] + b[0][1])) / 2;
        projection.scale(150 * k).translate([x, y]);
      }, object);
    }

    var maxDepth = 16, // maximum depth of subdivision
        cosMinDistance = cos(30 * radians$1); // cos(minimum angular distance)

    function resample(project, delta2) {
      return +delta2 ? resample$1(project, delta2) : resampleNone(project);
    }

    function resampleNone(project) {
      return transformer({
        point: function(x, y) {
          x = project(x, y);
          this.stream.point(x[0], x[1]);
        }
      });
    }

    function resample$1(project, delta2) {

      function resampleLineTo(x0, y0, lambda0, a0, b0, c0, x1, y1, lambda1, a1, b1, c1, depth, stream) {
        var dx = x1 - x0,
            dy = y1 - y0,
            d2 = dx * dx + dy * dy;
        if (d2 > 4 * delta2 && depth--) {
          var a = a0 + a1,
              b = b0 + b1,
              c = c0 + c1,
              m = sqrt(a * a + b * b + c * c),
              phi2 = asin(c /= m),
              lambda2 = abs(abs(c) - 1) < epsilon || abs(lambda0 - lambda1) < epsilon ? (lambda0 + lambda1) / 2 : atan2(b, a),
              p = project(lambda2, phi2),
              x2 = p[0],
              y2 = p[1],
              dx2 = x2 - x0,
              dy2 = y2 - y0,
              dz = dy * dx2 - dx * dy2;
          if (dz * dz / d2 > delta2 // perpendicular projected distance
              || abs((dx * dx2 + dy * dy2) / d2 - 0.5) > 0.3 // midpoint close to an end
              || a0 * a1 + b0 * b1 + c0 * c1 < cosMinDistance) { // angular distance
            resampleLineTo(x0, y0, lambda0, a0, b0, c0, x2, y2, lambda2, a /= m, b /= m, c, depth, stream);
            stream.point(x2, y2);
            resampleLineTo(x2, y2, lambda2, a, b, c, x1, y1, lambda1, a1, b1, c1, depth, stream);
          }
        }
      }
      return function(stream) {
        var lambda00, x00, y00, a00, b00, c00, // first point
            lambda0, x0, y0, a0, b0, c0; // previous point

        var resampleStream = {
          point: point,
          lineStart: lineStart,
          lineEnd: lineEnd,
          polygonStart: function() { stream.polygonStart(); resampleStream.lineStart = ringStart; },
          polygonEnd: function() { stream.polygonEnd(); resampleStream.lineStart = lineStart; }
        };

        function point(x, y) {
          x = project(x, y);
          stream.point(x[0], x[1]);
        }

        function lineStart() {
          x0 = NaN;
          resampleStream.point = linePoint;
          stream.lineStart();
        }

        function linePoint(lambda, phi) {
          var c = cartesian([lambda, phi]), p = project(lambda, phi);
          resampleLineTo(x0, y0, lambda0, a0, b0, c0, x0 = p[0], y0 = p[1], lambda0 = lambda, a0 = c[0], b0 = c[1], c0 = c[2], maxDepth, stream);
          stream.point(x0, y0);
        }

        function lineEnd() {
          resampleStream.point = point;
          stream.lineEnd();
        }

        function ringStart() {
          lineStart();
          resampleStream.point = ringPoint;
          resampleStream.lineEnd = ringEnd;
        }

        function ringPoint(lambda, phi) {
          linePoint(lambda00 = lambda, phi), x00 = x0, y00 = y0, a00 = a0, b00 = b0, c00 = c0;
          resampleStream.point = linePoint;
        }

        function ringEnd() {
          resampleLineTo(x0, y0, lambda0, a0, b0, c0, x00, y00, lambda00, a00, b00, c00, maxDepth, stream);
          resampleStream.lineEnd = lineEnd;
          lineEnd();
        }

        return resampleStream;
      };
    }

    var transformRadians = transformer({
      point: function(x, y) {
        this.stream.point(x * radians$1, y * radians$1);
      }
    });

    function transformRotate(rotate) {
      return transformer({
        point: function(x, y) {
          var r = rotate(x, y);
          return this.stream.point(r[0], r[1]);
        }
      });
    }

    function scaleTranslate(k, dx, dy, sx, sy) {
      function transform(x, y) {
        x *= sx; y *= sy;
        return [dx + k * x, dy - k * y];
      }
      transform.invert = function(x, y) {
        return [(x - dx) / k * sx, (dy - y) / k * sy];
      };
      return transform;
    }

    function scaleTranslateRotate(k, dx, dy, sx, sy, alpha) {
      if (!alpha) return scaleTranslate(k, dx, dy, sx, sy);
      var cosAlpha = cos(alpha),
          sinAlpha = sin(alpha),
          a = cosAlpha * k,
          b = sinAlpha * k,
          ai = cosAlpha / k,
          bi = sinAlpha / k,
          ci = (sinAlpha * dy - cosAlpha * dx) / k,
          fi = (sinAlpha * dx + cosAlpha * dy) / k;
      function transform(x, y) {
        x *= sx; y *= sy;
        return [a * x - b * y + dx, dy - b * x - a * y];
      }
      transform.invert = function(x, y) {
        return [sx * (ai * x - bi * y + ci), sy * (fi - bi * x - ai * y)];
      };
      return transform;
    }

    function projection(project) {
      return projectionMutator(function() { return project; })();
    }

    function projectionMutator(projectAt) {
      var project,
          k = 150, // scale
          x = 480, y = 250, // translate
          lambda = 0, phi = 0, // center
          deltaLambda = 0, deltaPhi = 0, deltaGamma = 0, rotate, // pre-rotate
          alpha = 0, // post-rotate angle
          sx = 1, // reflectX
          sy = 1, // reflectX
          theta = null, preclip = clipAntimeridian, // pre-clip angle
          x0 = null, y0, x1, y1, postclip = identity$1, // post-clip extent
          delta2 = 0.5, // precision
          projectResample,
          projectTransform,
          projectRotateTransform,
          cache,
          cacheStream;

      function projection(point) {
        return projectRotateTransform(point[0] * radians$1, point[1] * radians$1);
      }

      function invert(point) {
        point = projectRotateTransform.invert(point[0], point[1]);
        return point && [point[0] * degrees$1, point[1] * degrees$1];
      }

      projection.stream = function(stream) {
        return cache && cacheStream === stream ? cache : cache = transformRadians(transformRotate(rotate)(preclip(projectResample(postclip(cacheStream = stream)))));
      };

      projection.preclip = function(_) {
        return arguments.length ? (preclip = _, theta = undefined, reset()) : preclip;
      };

      projection.postclip = function(_) {
        return arguments.length ? (postclip = _, x0 = y0 = x1 = y1 = null, reset()) : postclip;
      };

      projection.clipAngle = function(_) {
        return arguments.length ? (preclip = +_ ? clipCircle(theta = _ * radians$1) : (theta = null, clipAntimeridian), reset()) : theta * degrees$1;
      };

      projection.clipExtent = function(_) {
        return arguments.length ? (postclip = _ == null ? (x0 = y0 = x1 = y1 = null, identity$1) : clipRectangle(x0 = +_[0][0], y0 = +_[0][1], x1 = +_[1][0], y1 = +_[1][1]), reset()) : x0 == null ? null : [[x0, y0], [x1, y1]];
      };

      projection.scale = function(_) {
        return arguments.length ? (k = +_, recenter()) : k;
      };

      projection.translate = function(_) {
        return arguments.length ? (x = +_[0], y = +_[1], recenter()) : [x, y];
      };

      projection.center = function(_) {
        return arguments.length ? (lambda = _[0] % 360 * radians$1, phi = _[1] % 360 * radians$1, recenter()) : [lambda * degrees$1, phi * degrees$1];
      };

      projection.rotate = function(_) {
        return arguments.length ? (deltaLambda = _[0] % 360 * radians$1, deltaPhi = _[1] % 360 * radians$1, deltaGamma = _.length > 2 ? _[2] % 360 * radians$1 : 0, recenter()) : [deltaLambda * degrees$1, deltaPhi * degrees$1, deltaGamma * degrees$1];
      };

      projection.angle = function(_) {
        return arguments.length ? (alpha = _ % 360 * radians$1, recenter()) : alpha * degrees$1;
      };

      projection.reflectX = function(_) {
        return arguments.length ? (sx = _ ? -1 : 1, recenter()) : sx < 0;
      };

      projection.reflectY = function(_) {
        return arguments.length ? (sy = _ ? -1 : 1, recenter()) : sy < 0;
      };

      projection.precision = function(_) {
        return arguments.length ? (projectResample = resample(projectTransform, delta2 = _ * _), reset()) : sqrt(delta2);
      };

      projection.fitExtent = function(extent, object) {
        return fitExtent(projection, extent, object);
      };

      projection.fitSize = function(size, object) {
        return fitSize(projection, size, object);
      };

      projection.fitWidth = function(width, object) {
        return fitWidth(projection, width, object);
      };

      projection.fitHeight = function(height, object) {
        return fitHeight(projection, height, object);
      };

      function recenter() {
        var center = scaleTranslateRotate(k, 0, 0, sx, sy, alpha).apply(null, project(lambda, phi)),
            transform = scaleTranslateRotate(k, x - center[0], y - center[1], sx, sy, alpha);
        rotate = rotateRadians(deltaLambda, deltaPhi, deltaGamma);
        projectTransform = compose(project, transform);
        projectRotateTransform = compose(rotate, projectTransform);
        projectResample = resample(projectTransform, delta2);
        return reset();
      }

      function reset() {
        cache = cacheStream = null;
        return projection;
      }

      return function() {
        project = projectAt.apply(this, arguments);
        projection.invert = project.invert && invert;
        return recenter();
      };
    }

    function conicProjection(projectAt) {
      var phi0 = 0,
          phi1 = pi / 3,
          m = projectionMutator(projectAt),
          p = m(phi0, phi1);

      p.parallels = function(_) {
        return arguments.length ? m(phi0 = _[0] * radians$1, phi1 = _[1] * radians$1) : [phi0 * degrees$1, phi1 * degrees$1];
      };

      return p;
    }

    function cylindricalEqualAreaRaw(phi0) {
      var cosPhi0 = cos(phi0);

      function forward(lambda, phi) {
        return [lambda * cosPhi0, sin(phi) / cosPhi0];
      }

      forward.invert = function(x, y) {
        return [x / cosPhi0, asin(y * cosPhi0)];
      };

      return forward;
    }

    function conicEqualAreaRaw(y0, y1) {
      var sy0 = sin(y0), n = (sy0 + sin(y1)) / 2;

      // Are the parallels symmetrical around the Equator?
      if (abs(n) < epsilon) return cylindricalEqualAreaRaw(y0);

      var c = 1 + sy0 * (2 * n - sy0), r0 = sqrt(c) / n;

      function project(x, y) {
        var r = sqrt(c - 2 * n * sin(y)) / n;
        return [r * sin(x *= n), r0 - r * cos(x)];
      }

      project.invert = function(x, y) {
        var r0y = r0 - y,
            l = atan2(x, abs(r0y)) * sign(r0y);
        if (r0y * n < 0)
          l -= pi * sign(x) * sign(r0y);
        return [l / n, asin((c - (x * x + r0y * r0y) * n * n) / (2 * n))];
      };

      return project;
    }

    function geoConicEqualArea() {
      return conicProjection(conicEqualAreaRaw)
          .scale(155.424)
          .center([0, 33.6442]);
    }

    function geoAlbers() {
      return geoConicEqualArea()
          .parallels([29.5, 45.5])
          .scale(1070)
          .translate([480, 250])
          .rotate([96, 0])
          .center([-0.6, 38.7]);
    }

    // The projections must have mutually exclusive clip regions on the sphere,
    // as this will avoid emitting interleaving lines and polygons.
    function multiplex(streams) {
      var n = streams.length;
      return {
        point: function(x, y) { var i = -1; while (++i < n) streams[i].point(x, y); },
        sphere: function() { var i = -1; while (++i < n) streams[i].sphere(); },
        lineStart: function() { var i = -1; while (++i < n) streams[i].lineStart(); },
        lineEnd: function() { var i = -1; while (++i < n) streams[i].lineEnd(); },
        polygonStart: function() { var i = -1; while (++i < n) streams[i].polygonStart(); },
        polygonEnd: function() { var i = -1; while (++i < n) streams[i].polygonEnd(); }
      };
    }

    // A composite projection for the United States, configured by default for
    // 960×500. The projection also works quite well at 960×600 if you change the
    // scale to 1285 and adjust the translate accordingly. The set of standard
    // parallels for each region comes from USGS, which is published here:
    // http://egsc.usgs.gov/isb/pubs/MapProjections/projections.html#albers
    function geoAlbersUsa() {
      var cache,
          cacheStream,
          lower48 = geoAlbers(), lower48Point,
          alaska = geoConicEqualArea().rotate([154, 0]).center([-2, 58.5]).parallels([55, 65]), alaskaPoint, // EPSG:3338
          hawaii = geoConicEqualArea().rotate([157, 0]).center([-3, 19.9]).parallels([8, 18]), hawaiiPoint, // ESRI:102007
          point, pointStream = {point: function(x, y) { point = [x, y]; }};

      function albersUsa(coordinates) {
        var x = coordinates[0], y = coordinates[1];
        return point = null,
            (lower48Point.point(x, y), point)
            || (alaskaPoint.point(x, y), point)
            || (hawaiiPoint.point(x, y), point);
      }

      albersUsa.invert = function(coordinates) {
        var k = lower48.scale(),
            t = lower48.translate(),
            x = (coordinates[0] - t[0]) / k,
            y = (coordinates[1] - t[1]) / k;
        return (y >= 0.120 && y < 0.234 && x >= -0.425 && x < -0.214 ? alaska
            : y >= 0.166 && y < 0.234 && x >= -0.214 && x < -0.115 ? hawaii
            : lower48).invert(coordinates);
      };

      albersUsa.stream = function(stream) {
        return cache && cacheStream === stream ? cache : cache = multiplex([lower48.stream(cacheStream = stream), alaska.stream(stream), hawaii.stream(stream)]);
      };

      albersUsa.precision = function(_) {
        if (!arguments.length) return lower48.precision();
        lower48.precision(_), alaska.precision(_), hawaii.precision(_);
        return reset();
      };

      albersUsa.scale = function(_) {
        if (!arguments.length) return lower48.scale();
        lower48.scale(_), alaska.scale(_ * 0.35), hawaii.scale(_);
        return albersUsa.translate(lower48.translate());
      };

      albersUsa.translate = function(_) {
        if (!arguments.length) return lower48.translate();
        var k = lower48.scale(), x = +_[0], y = +_[1];

        lower48Point = lower48
            .translate(_)
            .clipExtent([[x - 0.455 * k, y - 0.238 * k], [x + 0.455 * k, y + 0.238 * k]])
            .stream(pointStream);

        alaskaPoint = alaska
            .translate([x - 0.307 * k, y + 0.201 * k])
            .clipExtent([[x - 0.425 * k + epsilon, y + 0.120 * k + epsilon], [x - 0.214 * k - epsilon, y + 0.234 * k - epsilon]])
            .stream(pointStream);

        hawaiiPoint = hawaii
            .translate([x - 0.205 * k, y + 0.212 * k])
            .clipExtent([[x - 0.214 * k + epsilon, y + 0.166 * k + epsilon], [x - 0.115 * k - epsilon, y + 0.234 * k - epsilon]])
            .stream(pointStream);

        return reset();
      };

      albersUsa.fitExtent = function(extent, object) {
        return fitExtent(albersUsa, extent, object);
      };

      albersUsa.fitSize = function(size, object) {
        return fitSize(albersUsa, size, object);
      };

      albersUsa.fitWidth = function(width, object) {
        return fitWidth(albersUsa, width, object);
      };

      albersUsa.fitHeight = function(height, object) {
        return fitHeight(albersUsa, height, object);
      };

      function reset() {
        cache = cacheStream = null;
        return albersUsa;
      }

      return albersUsa.scale(1070);
    }

    function azimuthalRaw(scale) {
      return function(x, y) {
        var cx = cos(x),
            cy = cos(y),
            k = scale(cx * cy);
            if (k === Infinity) return [2, 0];
        return [
          k * cy * sin(x),
          k * sin(y)
        ];
      }
    }

    function azimuthalInvert(angle) {
      return function(x, y) {
        var z = sqrt(x * x + y * y),
            c = angle(z),
            sc = sin(c),
            cc = cos(c);
        return [
          atan2(x * sc, z * cc),
          asin(z && y * sc / z)
        ];
      }
    }

    var azimuthalEqualAreaRaw = azimuthalRaw(function(cxcy) {
      return sqrt(2 / (1 + cxcy));
    });

    azimuthalEqualAreaRaw.invert = azimuthalInvert(function(z) {
      return 2 * asin(z / 2);
    });

    function geoAzimuthalEqualArea() {
      return projection(azimuthalEqualAreaRaw)
          .scale(124.75)
          .clipAngle(180 - 1e-3);
    }

    var azimuthalEquidistantRaw = azimuthalRaw(function(c) {
      return (c = acos(c)) && c / sin(c);
    });

    azimuthalEquidistantRaw.invert = azimuthalInvert(function(z) {
      return z;
    });

    function geoAzimuthalEquidistant() {
      return projection(azimuthalEquidistantRaw)
          .scale(79.4188)
          .clipAngle(180 - 1e-3);
    }

    function mercatorRaw(lambda, phi) {
      return [lambda, log(tan((halfPi + phi) / 2))];
    }

    mercatorRaw.invert = function(x, y) {
      return [x, 2 * atan(exp(y)) - halfPi];
    };

    function geoMercator() {
      return mercatorProjection(mercatorRaw)
          .scale(961 / tau);
    }

    function mercatorProjection(project) {
      var m = projection(project),
          center = m.center,
          scale = m.scale,
          translate = m.translate,
          clipExtent = m.clipExtent,
          x0 = null, y0, x1, y1; // clip extent

      m.scale = function(_) {
        return arguments.length ? (scale(_), reclip()) : scale();
      };

      m.translate = function(_) {
        return arguments.length ? (translate(_), reclip()) : translate();
      };

      m.center = function(_) {
        return arguments.length ? (center(_), reclip()) : center();
      };

      m.clipExtent = function(_) {
        return arguments.length ? ((_ == null ? x0 = y0 = x1 = y1 = null : (x0 = +_[0][0], y0 = +_[0][1], x1 = +_[1][0], y1 = +_[1][1])), reclip()) : x0 == null ? null : [[x0, y0], [x1, y1]];
      };

      function reclip() {
        var k = pi * scale(),
            t = m(rotation(m.rotate()).invert([0, 0]));
        return clipExtent(x0 == null
            ? [[t[0] - k, t[1] - k], [t[0] + k, t[1] + k]] : project === mercatorRaw
            ? [[Math.max(t[0] - k, x0), y0], [Math.min(t[0] + k, x1), y1]]
            : [[x0, Math.max(t[1] - k, y0)], [x1, Math.min(t[1] + k, y1)]]);
      }

      return reclip();
    }

    function tany(y) {
      return tan((halfPi + y) / 2);
    }

    function conicConformalRaw(y0, y1) {
      var cy0 = cos(y0),
          n = y0 === y1 ? sin(y0) : log(cy0 / cos(y1)) / log(tany(y1) / tany(y0)),
          f = cy0 * pow(tany(y0), n) / n;

      if (!n) return mercatorRaw;

      function project(x, y) {
        if (f > 0) { if (y < -halfPi + epsilon) y = -halfPi + epsilon; }
        else { if (y > halfPi - epsilon) y = halfPi - epsilon; }
        var r = f / pow(tany(y), n);
        return [r * sin(n * x), f - r * cos(n * x)];
      }

      project.invert = function(x, y) {
        var fy = f - y, r = sign(n) * sqrt(x * x + fy * fy),
          l = atan2(x, abs(fy)) * sign(fy);
        if (fy * n < 0)
          l -= pi * sign(x) * sign(fy);
        return [l / n, 2 * atan(pow(f / r, 1 / n)) - halfPi];
      };

      return project;
    }

    function geoConicConformal() {
      return conicProjection(conicConformalRaw)
          .scale(109.5)
          .parallels([30, 30]);
    }

    function equirectangularRaw(lambda, phi) {
      return [lambda, phi];
    }

    equirectangularRaw.invert = equirectangularRaw;

    function geoEquirectangular() {
      return projection(equirectangularRaw)
          .scale(152.63);
    }

    function conicEquidistantRaw(y0, y1) {
      var cy0 = cos(y0),
          n = y0 === y1 ? sin(y0) : (cy0 - cos(y1)) / (y1 - y0),
          g = cy0 / n + y0;

      if (abs(n) < epsilon) return equirectangularRaw;

      function project(x, y) {
        var gy = g - y, nx = n * x;
        return [gy * sin(nx), g - gy * cos(nx)];
      }

      project.invert = function(x, y) {
        var gy = g - y,
            l = atan2(x, abs(gy)) * sign(gy);
        if (gy * n < 0)
          l -= pi * sign(x) * sign(gy);
        return [l / n, g - sign(n) * sqrt(x * x + gy * gy)];
      };

      return project;
    }

    function geoConicEquidistant() {
      return conicProjection(conicEquidistantRaw)
          .scale(131.154)
          .center([0, 13.9389]);
    }

    var A1 = 1.340264,
        A2 = -0.081106,
        A3 = 0.000893,
        A4 = 0.003796,
        M = sqrt(3) / 2,
        iterations = 12;

    function equalEarthRaw(lambda, phi) {
      var l = asin(M * sin(phi)), l2 = l * l, l6 = l2 * l2 * l2;
      return [
        lambda * cos(l) / (M * (A1 + 3 * A2 * l2 + l6 * (7 * A3 + 9 * A4 * l2))),
        l * (A1 + A2 * l2 + l6 * (A3 + A4 * l2))
      ];
    }

    equalEarthRaw.invert = function(x, y) {
      var l = y, l2 = l * l, l6 = l2 * l2 * l2;
      for (var i = 0, delta, fy, fpy; i < iterations; ++i) {
        fy = l * (A1 + A2 * l2 + l6 * (A3 + A4 * l2)) - y;
        fpy = A1 + 3 * A2 * l2 + l6 * (7 * A3 + 9 * A4 * l2);
        l -= delta = fy / fpy, l2 = l * l, l6 = l2 * l2 * l2;
        if (abs(delta) < epsilon2) break;
      }
      return [
        M * x * (A1 + 3 * A2 * l2 + l6 * (7 * A3 + 9 * A4 * l2)) / cos(l),
        asin(sin(l) / M)
      ];
    };

    function geoEqualEarth() {
      return projection(equalEarthRaw)
          .scale(177.158);
    }

    function gnomonicRaw(x, y) {
      var cy = cos(y), k = cos(x) * cy;
      return [cy * sin(x) / k, sin(y) / k];
    }

    gnomonicRaw.invert = azimuthalInvert(atan);

    function geoGnomonic() {
      return projection(gnomonicRaw)
          .scale(144.049)
          .clipAngle(60);
    }

    function naturalEarth1Raw(lambda, phi) {
      var phi2 = phi * phi, phi4 = phi2 * phi2;
      return [
        lambda * (0.8707 - 0.131979 * phi2 + phi4 * (-0.013791 + phi4 * (0.003971 * phi2 - 0.001529 * phi4))),
        phi * (1.007226 + phi2 * (0.015085 + phi4 * (-0.044475 + 0.028874 * phi2 - 0.005916 * phi4)))
      ];
    }

    naturalEarth1Raw.invert = function(x, y) {
      var phi = y, i = 25, delta;
      do {
        var phi2 = phi * phi, phi4 = phi2 * phi2;
        phi -= delta = (phi * (1.007226 + phi2 * (0.015085 + phi4 * (-0.044475 + 0.028874 * phi2 - 0.005916 * phi4))) - y) /
            (1.007226 + phi2 * (0.015085 * 3 + phi4 * (-0.044475 * 7 + 0.028874 * 9 * phi2 - 0.005916 * 11 * phi4)));
      } while (abs(delta) > epsilon && --i > 0);
      return [
        x / (0.8707 + (phi2 = phi * phi) * (-0.131979 + phi2 * (-0.013791 + phi2 * phi2 * phi2 * (0.003971 - 0.001529 * phi2)))),
        phi
      ];
    };

    function geoNaturalEarth1() {
      return projection(naturalEarth1Raw)
          .scale(175.295);
    }

    function orthographicRaw(x, y) {
      return [cos(y) * sin(x), sin(y)];
    }

    orthographicRaw.invert = azimuthalInvert(asin);

    function geoOrthographic() {
      return projection(orthographicRaw)
          .scale(249.5)
          .clipAngle(90 + epsilon);
    }

    function stereographicRaw(x, y) {
      var cy = cos(y), k = 1 + cos(x) * cy;
      return [cy * sin(x) / k, sin(y) / k];
    }

    stereographicRaw.invert = azimuthalInvert(function(z) {
      return 2 * atan(z);
    });

    function geoStereographic() {
      return projection(stereographicRaw)
          .scale(250)
          .clipAngle(142);
    }

    function transverseMercatorRaw(lambda, phi) {
      return [log(tan((halfPi + phi) / 2)), -lambda];
    }

    transverseMercatorRaw.invert = function(x, y) {
      return [-y, 2 * atan(exp(x)) - halfPi];
    };

    function geoTransverseMercator() {
      var m = mercatorProjection(transverseMercatorRaw),
          center = m.center,
          rotate = m.rotate;

      m.center = function(_) {
        return arguments.length ? center([-_[1], _[0]]) : (_ = center(), [_[1], -_[0]]);
      };

      m.rotate = function(_) {
        return arguments.length ? rotate([_[0], _[1], _.length > 2 ? _[2] + 90 : 90]) : (_ = rotate(), [_[0], _[1], _[2] - 90]);
      };

      return rotate([0, 0, 90])
          .scale(159.155);
    }

    const lookup$1 = {
        geoAzimuthalEqualArea,
        geoAzimuthalEquidistant,
        geoGnomonic,
        geoOrthographic,
        geoStereographic,
        geoEqualEarth,
        geoAlbers,
        geoAlbersUsa,
        geoConicConformal,
        geoConicEqualArea,
        geoConicEquidistant,
        geoEquirectangular,
        geoMercator,
        geoTransverseMercator,
        geoNaturalEarth1,
    };
    Object.keys(lookup$1).forEach((key) => {
        lookup$1[`${key.charAt(3).toLowerCase()}${key.slice(4)}`] = lookup$1[key];
    });
    class ProjectionScale extends chart_js.Scale {
        constructor(cfg) {
            super(cfg);
            this.outlineBounds = null;
            this.oldChartBounds = null;
            this.geoPath = geoPath();
        }
        init(options) {
            options.position = 'chartArea';
            super.init(options);
            if (typeof options.projection === 'function') {
                this.projection = options.projection;
            }
            else {
                this.projection = (lookup$1[options.projection] || lookup$1.albersUsa)();
            }
            this.geoPath.projection(this.projection);
            this.outlineBounds = null;
            this.oldChartBounds = null;
        }
        computeBounds(outline) {
            const bb = geoPath(this.projection.fitWidth(1000, outline)).bounds(outline);
            const bHeight = Math.ceil(bb[1][1] - bb[0][1]);
            const bWidth = Math.ceil(bb[1][0] - bb[0][0]);
            const t = this.projection.translate();
            this.outlineBounds = {
                width: bWidth,
                height: bHeight,
                aspectRatio: bWidth / bHeight,
                refScale: this.projection.scale(),
                refX: t[0],
                refY: t[1],
            };
        }
        updateBounds() {
            const area = this.chart.chartArea;
            const bb = this.outlineBounds;
            if (!bb) {
                return false;
            }
            const padding = this.options.padding;
            const paddingTop = typeof padding === 'number' ? padding : padding.top;
            const paddingLeft = typeof padding === 'number' ? padding : padding.left;
            const paddingBottom = typeof padding === 'number' ? padding : padding.bottom;
            const paddingRight = typeof padding === 'number' ? padding : padding.right;
            const chartWidth = area.right - area.left - paddingLeft - paddingRight;
            const chartHeight = area.bottom - area.top - paddingTop - paddingBottom;
            const bak = this.oldChartBounds;
            this.oldChartBounds = {
                chartWidth,
                chartHeight,
            };
            const scale = Math.min(chartWidth / bb.width, chartHeight / bb.height);
            const viewWidth = bb.width * scale;
            const viewHeight = bb.height * scale;
            const x = (chartWidth - viewWidth) * 0.5 + area.left + paddingLeft;
            const y = (chartHeight - viewHeight) * 0.5 + area.top + paddingTop;
            const o = this.options;
            this.projection
                .scale(bb.refScale * scale * o.projectionScale)
                .translate([scale * bb.refX + x + o.projectionOffset[0], scale * bb.refY + y + o.projectionOffset[1]]);
            return (!bak || bak.chartWidth !== this.oldChartBounds.chartWidth || bak.chartHeight !== this.oldChartBounds.chartHeight);
        }
    }
    ProjectionScale.id = 'projection';
    ProjectionScale.defaults = {
        projection: 'albersUsa',
        projectionScale: 1,
        projectionOffset: [0, 0],
        padding: 0,
    };
    ProjectionScale.descriptors = {
        _scriptable: (name) => name !== 'projection',
        _indexable: (name) => name !== 'projectionOffset',
    };

    function colors(specifier) {
      var n = specifier.length / 6 | 0, colors = new Array(n), i = 0;
      while (i < n) colors[i] = "#" + specifier.slice(i * 6, ++i * 6);
      return colors;
    }

    function define(constructor, factory, prototype) {
      constructor.prototype = factory.prototype = prototype;
      prototype.constructor = constructor;
    }

    function extend(parent, definition) {
      var prototype = Object.create(parent.prototype);
      for (var key in definition) prototype[key] = definition[key];
      return prototype;
    }

    function Color() {}

    var darker = 0.7;
    var brighter = 1 / darker;

    var reI = "\\s*([+-]?\\d+)\\s*",
        reN = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*",
        reP = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
        reHex = /^#([0-9a-f]{3,8})$/,
        reRgbInteger = new RegExp(`^rgb\\(${reI},${reI},${reI}\\)$`),
        reRgbPercent = new RegExp(`^rgb\\(${reP},${reP},${reP}\\)$`),
        reRgbaInteger = new RegExp(`^rgba\\(${reI},${reI},${reI},${reN}\\)$`),
        reRgbaPercent = new RegExp(`^rgba\\(${reP},${reP},${reP},${reN}\\)$`),
        reHslPercent = new RegExp(`^hsl\\(${reN},${reP},${reP}\\)$`),
        reHslaPercent = new RegExp(`^hsla\\(${reN},${reP},${reP},${reN}\\)$`);

    var named = {
      aliceblue: 0xf0f8ff,
      antiquewhite: 0xfaebd7,
      aqua: 0x00ffff,
      aquamarine: 0x7fffd4,
      azure: 0xf0ffff,
      beige: 0xf5f5dc,
      bisque: 0xffe4c4,
      black: 0x000000,
      blanchedalmond: 0xffebcd,
      blue: 0x0000ff,
      blueviolet: 0x8a2be2,
      brown: 0xa52a2a,
      burlywood: 0xdeb887,
      cadetblue: 0x5f9ea0,
      chartreuse: 0x7fff00,
      chocolate: 0xd2691e,
      coral: 0xff7f50,
      cornflowerblue: 0x6495ed,
      cornsilk: 0xfff8dc,
      crimson: 0xdc143c,
      cyan: 0x00ffff,
      darkblue: 0x00008b,
      darkcyan: 0x008b8b,
      darkgoldenrod: 0xb8860b,
      darkgray: 0xa9a9a9,
      darkgreen: 0x006400,
      darkgrey: 0xa9a9a9,
      darkkhaki: 0xbdb76b,
      darkmagenta: 0x8b008b,
      darkolivegreen: 0x556b2f,
      darkorange: 0xff8c00,
      darkorchid: 0x9932cc,
      darkred: 0x8b0000,
      darksalmon: 0xe9967a,
      darkseagreen: 0x8fbc8f,
      darkslateblue: 0x483d8b,
      darkslategray: 0x2f4f4f,
      darkslategrey: 0x2f4f4f,
      darkturquoise: 0x00ced1,
      darkviolet: 0x9400d3,
      deeppink: 0xff1493,
      deepskyblue: 0x00bfff,
      dimgray: 0x696969,
      dimgrey: 0x696969,
      dodgerblue: 0x1e90ff,
      firebrick: 0xb22222,
      floralwhite: 0xfffaf0,
      forestgreen: 0x228b22,
      fuchsia: 0xff00ff,
      gainsboro: 0xdcdcdc,
      ghostwhite: 0xf8f8ff,
      gold: 0xffd700,
      goldenrod: 0xdaa520,
      gray: 0x808080,
      green: 0x008000,
      greenyellow: 0xadff2f,
      grey: 0x808080,
      honeydew: 0xf0fff0,
      hotpink: 0xff69b4,
      indianred: 0xcd5c5c,
      indigo: 0x4b0082,
      ivory: 0xfffff0,
      khaki: 0xf0e68c,
      lavender: 0xe6e6fa,
      lavenderblush: 0xfff0f5,
      lawngreen: 0x7cfc00,
      lemonchiffon: 0xfffacd,
      lightblue: 0xadd8e6,
      lightcoral: 0xf08080,
      lightcyan: 0xe0ffff,
      lightgoldenrodyellow: 0xfafad2,
      lightgray: 0xd3d3d3,
      lightgreen: 0x90ee90,
      lightgrey: 0xd3d3d3,
      lightpink: 0xffb6c1,
      lightsalmon: 0xffa07a,
      lightseagreen: 0x20b2aa,
      lightskyblue: 0x87cefa,
      lightslategray: 0x778899,
      lightslategrey: 0x778899,
      lightsteelblue: 0xb0c4de,
      lightyellow: 0xffffe0,
      lime: 0x00ff00,
      limegreen: 0x32cd32,
      linen: 0xfaf0e6,
      magenta: 0xff00ff,
      maroon: 0x800000,
      mediumaquamarine: 0x66cdaa,
      mediumblue: 0x0000cd,
      mediumorchid: 0xba55d3,
      mediumpurple: 0x9370db,
      mediumseagreen: 0x3cb371,
      mediumslateblue: 0x7b68ee,
      mediumspringgreen: 0x00fa9a,
      mediumturquoise: 0x48d1cc,
      mediumvioletred: 0xc71585,
      midnightblue: 0x191970,
      mintcream: 0xf5fffa,
      mistyrose: 0xffe4e1,
      moccasin: 0xffe4b5,
      navajowhite: 0xffdead,
      navy: 0x000080,
      oldlace: 0xfdf5e6,
      olive: 0x808000,
      olivedrab: 0x6b8e23,
      orange: 0xffa500,
      orangered: 0xff4500,
      orchid: 0xda70d6,
      palegoldenrod: 0xeee8aa,
      palegreen: 0x98fb98,
      paleturquoise: 0xafeeee,
      palevioletred: 0xdb7093,
      papayawhip: 0xffefd5,
      peachpuff: 0xffdab9,
      peru: 0xcd853f,
      pink: 0xffc0cb,
      plum: 0xdda0dd,
      powderblue: 0xb0e0e6,
      purple: 0x800080,
      rebeccapurple: 0x663399,
      red: 0xff0000,
      rosybrown: 0xbc8f8f,
      royalblue: 0x4169e1,
      saddlebrown: 0x8b4513,
      salmon: 0xfa8072,
      sandybrown: 0xf4a460,
      seagreen: 0x2e8b57,
      seashell: 0xfff5ee,
      sienna: 0xa0522d,
      silver: 0xc0c0c0,
      skyblue: 0x87ceeb,
      slateblue: 0x6a5acd,
      slategray: 0x708090,
      slategrey: 0x708090,
      snow: 0xfffafa,
      springgreen: 0x00ff7f,
      steelblue: 0x4682b4,
      tan: 0xd2b48c,
      teal: 0x008080,
      thistle: 0xd8bfd8,
      tomato: 0xff6347,
      turquoise: 0x40e0d0,
      violet: 0xee82ee,
      wheat: 0xf5deb3,
      white: 0xffffff,
      whitesmoke: 0xf5f5f5,
      yellow: 0xffff00,
      yellowgreen: 0x9acd32
    };

    define(Color, color, {
      copy(channels) {
        return Object.assign(new this.constructor, this, channels);
      },
      displayable() {
        return this.rgb().displayable();
      },
      hex: color_formatHex, // Deprecated! Use color.formatHex.
      formatHex: color_formatHex,
      formatHex8: color_formatHex8,
      formatHsl: color_formatHsl,
      formatRgb: color_formatRgb,
      toString: color_formatRgb
    });

    function color_formatHex() {
      return this.rgb().formatHex();
    }

    function color_formatHex8() {
      return this.rgb().formatHex8();
    }

    function color_formatHsl() {
      return hslConvert(this).formatHsl();
    }

    function color_formatRgb() {
      return this.rgb().formatRgb();
    }

    function color(format) {
      var m, l;
      format = (format + "").trim().toLowerCase();
      return (m = reHex.exec(format)) ? (l = m[1].length, m = parseInt(m[1], 16), l === 6 ? rgbn(m) // #ff0000
          : l === 3 ? new Rgb((m >> 8 & 0xf) | (m >> 4 & 0xf0), (m >> 4 & 0xf) | (m & 0xf0), ((m & 0xf) << 4) | (m & 0xf), 1) // #f00
          : l === 8 ? rgba(m >> 24 & 0xff, m >> 16 & 0xff, m >> 8 & 0xff, (m & 0xff) / 0xff) // #ff000000
          : l === 4 ? rgba((m >> 12 & 0xf) | (m >> 8 & 0xf0), (m >> 8 & 0xf) | (m >> 4 & 0xf0), (m >> 4 & 0xf) | (m & 0xf0), (((m & 0xf) << 4) | (m & 0xf)) / 0xff) // #f000
          : null) // invalid hex
          : (m = reRgbInteger.exec(format)) ? new Rgb(m[1], m[2], m[3], 1) // rgb(255, 0, 0)
          : (m = reRgbPercent.exec(format)) ? new Rgb(m[1] * 255 / 100, m[2] * 255 / 100, m[3] * 255 / 100, 1) // rgb(100%, 0%, 0%)
          : (m = reRgbaInteger.exec(format)) ? rgba(m[1], m[2], m[3], m[4]) // rgba(255, 0, 0, 1)
          : (m = reRgbaPercent.exec(format)) ? rgba(m[1] * 255 / 100, m[2] * 255 / 100, m[3] * 255 / 100, m[4]) // rgb(100%, 0%, 0%, 1)
          : (m = reHslPercent.exec(format)) ? hsla(m[1], m[2] / 100, m[3] / 100, 1) // hsl(120, 50%, 50%)
          : (m = reHslaPercent.exec(format)) ? hsla(m[1], m[2] / 100, m[3] / 100, m[4]) // hsla(120, 50%, 50%, 1)
          : named.hasOwnProperty(format) ? rgbn(named[format]) // eslint-disable-line no-prototype-builtins
          : format === "transparent" ? new Rgb(NaN, NaN, NaN, 0)
          : null;
    }

    function rgbn(n) {
      return new Rgb(n >> 16 & 0xff, n >> 8 & 0xff, n & 0xff, 1);
    }

    function rgba(r, g, b, a) {
      if (a <= 0) r = g = b = NaN;
      return new Rgb(r, g, b, a);
    }

    function rgbConvert(o) {
      if (!(o instanceof Color)) o = color(o);
      if (!o) return new Rgb;
      o = o.rgb();
      return new Rgb(o.r, o.g, o.b, o.opacity);
    }

    function rgb(r, g, b, opacity) {
      return arguments.length === 1 ? rgbConvert(r) : new Rgb(r, g, b, opacity == null ? 1 : opacity);
    }

    function Rgb(r, g, b, opacity) {
      this.r = +r;
      this.g = +g;
      this.b = +b;
      this.opacity = +opacity;
    }

    define(Rgb, rgb, extend(Color, {
      brighter(k) {
        k = k == null ? brighter : Math.pow(brighter, k);
        return new Rgb(this.r * k, this.g * k, this.b * k, this.opacity);
      },
      darker(k) {
        k = k == null ? darker : Math.pow(darker, k);
        return new Rgb(this.r * k, this.g * k, this.b * k, this.opacity);
      },
      rgb() {
        return this;
      },
      clamp() {
        return new Rgb(clampi(this.r), clampi(this.g), clampi(this.b), clampa(this.opacity));
      },
      displayable() {
        return (-0.5 <= this.r && this.r < 255.5)
            && (-0.5 <= this.g && this.g < 255.5)
            && (-0.5 <= this.b && this.b < 255.5)
            && (0 <= this.opacity && this.opacity <= 1);
      },
      hex: rgb_formatHex, // Deprecated! Use color.formatHex.
      formatHex: rgb_formatHex,
      formatHex8: rgb_formatHex8,
      formatRgb: rgb_formatRgb,
      toString: rgb_formatRgb
    }));

    function rgb_formatHex() {
      return `#${hex(this.r)}${hex(this.g)}${hex(this.b)}`;
    }

    function rgb_formatHex8() {
      return `#${hex(this.r)}${hex(this.g)}${hex(this.b)}${hex((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
    }

    function rgb_formatRgb() {
      const a = clampa(this.opacity);
      return `${a === 1 ? "rgb(" : "rgba("}${clampi(this.r)}, ${clampi(this.g)}, ${clampi(this.b)}${a === 1 ? ")" : `, ${a})`}`;
    }

    function clampa(opacity) {
      return isNaN(opacity) ? 1 : Math.max(0, Math.min(1, opacity));
    }

    function clampi(value) {
      return Math.max(0, Math.min(255, Math.round(value) || 0));
    }

    function hex(value) {
      value = clampi(value);
      return (value < 16 ? "0" : "") + value.toString(16);
    }

    function hsla(h, s, l, a) {
      if (a <= 0) h = s = l = NaN;
      else if (l <= 0 || l >= 1) h = s = NaN;
      else if (s <= 0) h = NaN;
      return new Hsl(h, s, l, a);
    }

    function hslConvert(o) {
      if (o instanceof Hsl) return new Hsl(o.h, o.s, o.l, o.opacity);
      if (!(o instanceof Color)) o = color(o);
      if (!o) return new Hsl;
      if (o instanceof Hsl) return o;
      o = o.rgb();
      var r = o.r / 255,
          g = o.g / 255,
          b = o.b / 255,
          min = Math.min(r, g, b),
          max = Math.max(r, g, b),
          h = NaN,
          s = max - min,
          l = (max + min) / 2;
      if (s) {
        if (r === max) h = (g - b) / s + (g < b) * 6;
        else if (g === max) h = (b - r) / s + 2;
        else h = (r - g) / s + 4;
        s /= l < 0.5 ? max + min : 2 - max - min;
        h *= 60;
      } else {
        s = l > 0 && l < 1 ? 0 : h;
      }
      return new Hsl(h, s, l, o.opacity);
    }

    function hsl(h, s, l, opacity) {
      return arguments.length === 1 ? hslConvert(h) : new Hsl(h, s, l, opacity == null ? 1 : opacity);
    }

    function Hsl(h, s, l, opacity) {
      this.h = +h;
      this.s = +s;
      this.l = +l;
      this.opacity = +opacity;
    }

    define(Hsl, hsl, extend(Color, {
      brighter(k) {
        k = k == null ? brighter : Math.pow(brighter, k);
        return new Hsl(this.h, this.s, this.l * k, this.opacity);
      },
      darker(k) {
        k = k == null ? darker : Math.pow(darker, k);
        return new Hsl(this.h, this.s, this.l * k, this.opacity);
      },
      rgb() {
        var h = this.h % 360 + (this.h < 0) * 360,
            s = isNaN(h) || isNaN(this.s) ? 0 : this.s,
            l = this.l,
            m2 = l + (l < 0.5 ? l : 1 - l) * s,
            m1 = 2 * l - m2;
        return new Rgb(
          hsl2rgb(h >= 240 ? h - 240 : h + 120, m1, m2),
          hsl2rgb(h, m1, m2),
          hsl2rgb(h < 120 ? h + 240 : h - 120, m1, m2),
          this.opacity
        );
      },
      clamp() {
        return new Hsl(clamph(this.h), clampt(this.s), clampt(this.l), clampa(this.opacity));
      },
      displayable() {
        return (0 <= this.s && this.s <= 1 || isNaN(this.s))
            && (0 <= this.l && this.l <= 1)
            && (0 <= this.opacity && this.opacity <= 1);
      },
      formatHsl() {
        const a = clampa(this.opacity);
        return `${a === 1 ? "hsl(" : "hsla("}${clamph(this.h)}, ${clampt(this.s) * 100}%, ${clampt(this.l) * 100}%${a === 1 ? ")" : `, ${a})`}`;
      }
    }));

    function clamph(value) {
      value = (value || 0) % 360;
      return value < 0 ? value + 360 : value;
    }

    function clampt(value) {
      return Math.max(0, Math.min(1, value || 0));
    }

    /* From FvD 13.37, CSS Color Module Level 3 */
    function hsl2rgb(h, m1, m2) {
      return (h < 60 ? m1 + (m2 - m1) * h / 60
          : h < 180 ? m2
          : h < 240 ? m1 + (m2 - m1) * (240 - h) / 60
          : m1) * 255;
    }

    const radians = Math.PI / 180;
    const degrees = 180 / Math.PI;

    var A = -0.14861,
        B = +1.78277,
        C = -0.29227,
        D = -0.90649,
        E = +1.97294,
        ED = E * D,
        EB = E * B,
        BC_DA = B * C - D * A;

    function cubehelixConvert(o) {
      if (o instanceof Cubehelix) return new Cubehelix(o.h, o.s, o.l, o.opacity);
      if (!(o instanceof Rgb)) o = rgbConvert(o);
      var r = o.r / 255,
          g = o.g / 255,
          b = o.b / 255,
          l = (BC_DA * b + ED * r - EB * g) / (BC_DA + ED - EB),
          bl = b - l,
          k = (E * (g - l) - C * bl) / D,
          s = Math.sqrt(k * k + bl * bl) / (E * l * (1 - l)), // NaN if l=0 or l=1
          h = s ? Math.atan2(k, bl) * degrees - 120 : NaN;
      return new Cubehelix(h < 0 ? h + 360 : h, s, l, o.opacity);
    }

    function cubehelix$1(h, s, l, opacity) {
      return arguments.length === 1 ? cubehelixConvert(h) : new Cubehelix(h, s, l, opacity == null ? 1 : opacity);
    }

    function Cubehelix(h, s, l, opacity) {
      this.h = +h;
      this.s = +s;
      this.l = +l;
      this.opacity = +opacity;
    }

    define(Cubehelix, cubehelix$1, extend(Color, {
      brighter(k) {
        k = k == null ? brighter : Math.pow(brighter, k);
        return new Cubehelix(this.h, this.s, this.l * k, this.opacity);
      },
      darker(k) {
        k = k == null ? darker : Math.pow(darker, k);
        return new Cubehelix(this.h, this.s, this.l * k, this.opacity);
      },
      rgb() {
        var h = isNaN(this.h) ? 0 : (this.h + 120) * radians,
            l = +this.l,
            a = isNaN(this.s) ? 0 : this.s * l * (1 - l),
            cosh = Math.cos(h),
            sinh = Math.sin(h);
        return new Rgb(
          255 * (l + a * (A * cosh + B * sinh)),
          255 * (l + a * (C * cosh + D * sinh)),
          255 * (l + a * (E * cosh)),
          this.opacity
        );
      }
    }));

    function basis(t1, v0, v1, v2, v3) {
      var t2 = t1 * t1, t3 = t2 * t1;
      return ((1 - 3 * t1 + 3 * t2 - t3) * v0
          + (4 - 6 * t2 + 3 * t3) * v1
          + (1 + 3 * t1 + 3 * t2 - 3 * t3) * v2
          + t3 * v3) / 6;
    }

    function basis$1(values) {
      var n = values.length - 1;
      return function(t) {
        var i = t <= 0 ? (t = 0) : t >= 1 ? (t = 1, n - 1) : Math.floor(t * n),
            v1 = values[i],
            v2 = values[i + 1],
            v0 = i > 0 ? values[i - 1] : 2 * v1 - v2,
            v3 = i < n - 1 ? values[i + 2] : 2 * v2 - v1;
        return basis((t - i / n) * n, v0, v1, v2, v3);
      };
    }

    var constant = x => () => x;

    function linear(a, d) {
      return function(t) {
        return a + t * d;
      };
    }

    function exponential(a, b, y) {
      return a = Math.pow(a, y), b = Math.pow(b, y) - a, y = 1 / y, function(t) {
        return Math.pow(a + t * b, y);
      };
    }

    function hue(a, b) {
      var d = b - a;
      return d ? linear(a, d > 180 || d < -180 ? d - 360 * Math.round(d / 360) : d) : constant(isNaN(a) ? b : a);
    }

    function gamma(y) {
      return (y = +y) === 1 ? nogamma : function(a, b) {
        return b - a ? exponential(a, b, y) : constant(isNaN(a) ? b : a);
      };
    }

    function nogamma(a, b) {
      var d = b - a;
      return d ? linear(a, d) : constant(isNaN(a) ? b : a);
    }

    ((function rgbGamma(y) {
      var color = gamma(y);

      function rgb$1(start, end) {
        var r = color((start = rgb(start)).r, (end = rgb(end)).r),
            g = color(start.g, end.g),
            b = color(start.b, end.b),
            opacity = nogamma(start.opacity, end.opacity);
        return function(t) {
          start.r = r(t);
          start.g = g(t);
          start.b = b(t);
          start.opacity = opacity(t);
          return start + "";
        };
      }

      rgb$1.gamma = rgbGamma;

      return rgb$1;
    }))(1);

    function rgbSpline(spline) {
      return function(colors) {
        var n = colors.length,
            r = new Array(n),
            g = new Array(n),
            b = new Array(n),
            i, color;
        for (i = 0; i < n; ++i) {
          color = rgb(colors[i]);
          r[i] = color.r || 0;
          g[i] = color.g || 0;
          b[i] = color.b || 0;
        }
        r = spline(r);
        g = spline(g);
        b = spline(b);
        color.opacity = 1;
        return function(t) {
          color.r = r(t);
          color.g = g(t);
          color.b = b(t);
          return color + "";
        };
      };
    }

    var rgbBasis = rgbSpline(basis$1);

    function cubehelix(hue) {
      return (function cubehelixGamma(y) {
        y = +y;

        function cubehelix(start, end) {
          var h = hue((start = cubehelix$1(start)).h, (end = cubehelix$1(end)).h),
              s = nogamma(start.s, end.s),
              l = nogamma(start.l, end.l),
              opacity = nogamma(start.opacity, end.opacity);
          return function(t) {
            start.h = h(t);
            start.s = s(t);
            start.l = l(Math.pow(t, y));
            start.opacity = opacity(t);
            return start + "";
          };
        }

        cubehelix.gamma = cubehelixGamma;

        return cubehelix;
      })(1);
    }

    cubehelix(hue);
    var cubehelixLong = cubehelix(nogamma);

    var ramp$1 = scheme => rgbBasis(scheme[scheme.length - 1]);

    var scheme$q = new Array(3).concat(
      "d8b365f5f5f55ab4ac",
      "a6611adfc27d80cdc1018571",
      "a6611adfc27df5f5f580cdc1018571",
      "8c510ad8b365f6e8c3c7eae55ab4ac01665e",
      "8c510ad8b365f6e8c3f5f5f5c7eae55ab4ac01665e",
      "8c510abf812ddfc27df6e8c3c7eae580cdc135978f01665e",
      "8c510abf812ddfc27df6e8c3f5f5f5c7eae580cdc135978f01665e",
      "5430058c510abf812ddfc27df6e8c3c7eae580cdc135978f01665e003c30",
      "5430058c510abf812ddfc27df6e8c3f5f5f5c7eae580cdc135978f01665e003c30"
    ).map(colors);

    var interpolateBrBG = ramp$1(scheme$q);

    var scheme$p = new Array(3).concat(
      "af8dc3f7f7f77fbf7b",
      "7b3294c2a5cfa6dba0008837",
      "7b3294c2a5cff7f7f7a6dba0008837",
      "762a83af8dc3e7d4e8d9f0d37fbf7b1b7837",
      "762a83af8dc3e7d4e8f7f7f7d9f0d37fbf7b1b7837",
      "762a839970abc2a5cfe7d4e8d9f0d3a6dba05aae611b7837",
      "762a839970abc2a5cfe7d4e8f7f7f7d9f0d3a6dba05aae611b7837",
      "40004b762a839970abc2a5cfe7d4e8d9f0d3a6dba05aae611b783700441b",
      "40004b762a839970abc2a5cfe7d4e8f7f7f7d9f0d3a6dba05aae611b783700441b"
    ).map(colors);

    var interpolatePRGn = ramp$1(scheme$p);

    var scheme$o = new Array(3).concat(
      "e9a3c9f7f7f7a1d76a",
      "d01c8bf1b6dab8e1864dac26",
      "d01c8bf1b6daf7f7f7b8e1864dac26",
      "c51b7de9a3c9fde0efe6f5d0a1d76a4d9221",
      "c51b7de9a3c9fde0eff7f7f7e6f5d0a1d76a4d9221",
      "c51b7dde77aef1b6dafde0efe6f5d0b8e1867fbc414d9221",
      "c51b7dde77aef1b6dafde0eff7f7f7e6f5d0b8e1867fbc414d9221",
      "8e0152c51b7dde77aef1b6dafde0efe6f5d0b8e1867fbc414d9221276419",
      "8e0152c51b7dde77aef1b6dafde0eff7f7f7e6f5d0b8e1867fbc414d9221276419"
    ).map(colors);

    var interpolatePiYG = ramp$1(scheme$o);

    var scheme$n = new Array(3).concat(
      "998ec3f7f7f7f1a340",
      "5e3c99b2abd2fdb863e66101",
      "5e3c99b2abd2f7f7f7fdb863e66101",
      "542788998ec3d8daebfee0b6f1a340b35806",
      "542788998ec3d8daebf7f7f7fee0b6f1a340b35806",
      "5427888073acb2abd2d8daebfee0b6fdb863e08214b35806",
      "5427888073acb2abd2d8daebf7f7f7fee0b6fdb863e08214b35806",
      "2d004b5427888073acb2abd2d8daebfee0b6fdb863e08214b358067f3b08",
      "2d004b5427888073acb2abd2d8daebf7f7f7fee0b6fdb863e08214b358067f3b08"
    ).map(colors);

    var interpolatePuOr = ramp$1(scheme$n);

    var scheme$m = new Array(3).concat(
      "ef8a62f7f7f767a9cf",
      "ca0020f4a58292c5de0571b0",
      "ca0020f4a582f7f7f792c5de0571b0",
      "b2182bef8a62fddbc7d1e5f067a9cf2166ac",
      "b2182bef8a62fddbc7f7f7f7d1e5f067a9cf2166ac",
      "b2182bd6604df4a582fddbc7d1e5f092c5de4393c32166ac",
      "b2182bd6604df4a582fddbc7f7f7f7d1e5f092c5de4393c32166ac",
      "67001fb2182bd6604df4a582fddbc7d1e5f092c5de4393c32166ac053061",
      "67001fb2182bd6604df4a582fddbc7f7f7f7d1e5f092c5de4393c32166ac053061"
    ).map(colors);

    var interpolateRdBu = ramp$1(scheme$m);

    var scheme$l = new Array(3).concat(
      "ef8a62ffffff999999",
      "ca0020f4a582bababa404040",
      "ca0020f4a582ffffffbababa404040",
      "b2182bef8a62fddbc7e0e0e09999994d4d4d",
      "b2182bef8a62fddbc7ffffffe0e0e09999994d4d4d",
      "b2182bd6604df4a582fddbc7e0e0e0bababa8787874d4d4d",
      "b2182bd6604df4a582fddbc7ffffffe0e0e0bababa8787874d4d4d",
      "67001fb2182bd6604df4a582fddbc7e0e0e0bababa8787874d4d4d1a1a1a",
      "67001fb2182bd6604df4a582fddbc7ffffffe0e0e0bababa8787874d4d4d1a1a1a"
    ).map(colors);

    var interpolateRdGy = ramp$1(scheme$l);

    var scheme$k = new Array(3).concat(
      "fc8d59ffffbf91bfdb",
      "d7191cfdae61abd9e92c7bb6",
      "d7191cfdae61ffffbfabd9e92c7bb6",
      "d73027fc8d59fee090e0f3f891bfdb4575b4",
      "d73027fc8d59fee090ffffbfe0f3f891bfdb4575b4",
      "d73027f46d43fdae61fee090e0f3f8abd9e974add14575b4",
      "d73027f46d43fdae61fee090ffffbfe0f3f8abd9e974add14575b4",
      "a50026d73027f46d43fdae61fee090e0f3f8abd9e974add14575b4313695",
      "a50026d73027f46d43fdae61fee090ffffbfe0f3f8abd9e974add14575b4313695"
    ).map(colors);

    var interpolateRdYlBu = ramp$1(scheme$k);

    var scheme$j = new Array(3).concat(
      "fc8d59ffffbf91cf60",
      "d7191cfdae61a6d96a1a9641",
      "d7191cfdae61ffffbfa6d96a1a9641",
      "d73027fc8d59fee08bd9ef8b91cf601a9850",
      "d73027fc8d59fee08bffffbfd9ef8b91cf601a9850",
      "d73027f46d43fdae61fee08bd9ef8ba6d96a66bd631a9850",
      "d73027f46d43fdae61fee08bffffbfd9ef8ba6d96a66bd631a9850",
      "a50026d73027f46d43fdae61fee08bd9ef8ba6d96a66bd631a9850006837",
      "a50026d73027f46d43fdae61fee08bffffbfd9ef8ba6d96a66bd631a9850006837"
    ).map(colors);

    var interpolateRdYlGn = ramp$1(scheme$j);

    var scheme$i = new Array(3).concat(
      "fc8d59ffffbf99d594",
      "d7191cfdae61abdda42b83ba",
      "d7191cfdae61ffffbfabdda42b83ba",
      "d53e4ffc8d59fee08be6f59899d5943288bd",
      "d53e4ffc8d59fee08bffffbfe6f59899d5943288bd",
      "d53e4ff46d43fdae61fee08be6f598abdda466c2a53288bd",
      "d53e4ff46d43fdae61fee08bffffbfe6f598abdda466c2a53288bd",
      "9e0142d53e4ff46d43fdae61fee08be6f598abdda466c2a53288bd5e4fa2",
      "9e0142d53e4ff46d43fdae61fee08bffffbfe6f598abdda466c2a53288bd5e4fa2"
    ).map(colors);

    var interpolateSpectral = ramp$1(scheme$i);

    var scheme$h = new Array(3).concat(
      "e5f5f999d8c92ca25f",
      "edf8fbb2e2e266c2a4238b45",
      "edf8fbb2e2e266c2a42ca25f006d2c",
      "edf8fbccece699d8c966c2a42ca25f006d2c",
      "edf8fbccece699d8c966c2a441ae76238b45005824",
      "f7fcfde5f5f9ccece699d8c966c2a441ae76238b45005824",
      "f7fcfde5f5f9ccece699d8c966c2a441ae76238b45006d2c00441b"
    ).map(colors);

    var interpolateBuGn = ramp$1(scheme$h);

    var scheme$g = new Array(3).concat(
      "e0ecf49ebcda8856a7",
      "edf8fbb3cde38c96c688419d",
      "edf8fbb3cde38c96c68856a7810f7c",
      "edf8fbbfd3e69ebcda8c96c68856a7810f7c",
      "edf8fbbfd3e69ebcda8c96c68c6bb188419d6e016b",
      "f7fcfde0ecf4bfd3e69ebcda8c96c68c6bb188419d6e016b",
      "f7fcfde0ecf4bfd3e69ebcda8c96c68c6bb188419d810f7c4d004b"
    ).map(colors);

    var interpolateBuPu = ramp$1(scheme$g);

    var scheme$f = new Array(3).concat(
      "e0f3dba8ddb543a2ca",
      "f0f9e8bae4bc7bccc42b8cbe",
      "f0f9e8bae4bc7bccc443a2ca0868ac",
      "f0f9e8ccebc5a8ddb57bccc443a2ca0868ac",
      "f0f9e8ccebc5a8ddb57bccc44eb3d32b8cbe08589e",
      "f7fcf0e0f3dbccebc5a8ddb57bccc44eb3d32b8cbe08589e",
      "f7fcf0e0f3dbccebc5a8ddb57bccc44eb3d32b8cbe0868ac084081"
    ).map(colors);

    var interpolateGnBu = ramp$1(scheme$f);

    var scheme$e = new Array(3).concat(
      "fee8c8fdbb84e34a33",
      "fef0d9fdcc8afc8d59d7301f",
      "fef0d9fdcc8afc8d59e34a33b30000",
      "fef0d9fdd49efdbb84fc8d59e34a33b30000",
      "fef0d9fdd49efdbb84fc8d59ef6548d7301f990000",
      "fff7ecfee8c8fdd49efdbb84fc8d59ef6548d7301f990000",
      "fff7ecfee8c8fdd49efdbb84fc8d59ef6548d7301fb300007f0000"
    ).map(colors);

    var interpolateOrRd = ramp$1(scheme$e);

    var scheme$d = new Array(3).concat(
      "ece2f0a6bddb1c9099",
      "f6eff7bdc9e167a9cf02818a",
      "f6eff7bdc9e167a9cf1c9099016c59",
      "f6eff7d0d1e6a6bddb67a9cf1c9099016c59",
      "f6eff7d0d1e6a6bddb67a9cf3690c002818a016450",
      "fff7fbece2f0d0d1e6a6bddb67a9cf3690c002818a016450",
      "fff7fbece2f0d0d1e6a6bddb67a9cf3690c002818a016c59014636"
    ).map(colors);

    var interpolatePuBuGn = ramp$1(scheme$d);

    var scheme$c = new Array(3).concat(
      "ece7f2a6bddb2b8cbe",
      "f1eef6bdc9e174a9cf0570b0",
      "f1eef6bdc9e174a9cf2b8cbe045a8d",
      "f1eef6d0d1e6a6bddb74a9cf2b8cbe045a8d",
      "f1eef6d0d1e6a6bddb74a9cf3690c00570b0034e7b",
      "fff7fbece7f2d0d1e6a6bddb74a9cf3690c00570b0034e7b",
      "fff7fbece7f2d0d1e6a6bddb74a9cf3690c00570b0045a8d023858"
    ).map(colors);

    var interpolatePuBu = ramp$1(scheme$c);

    var scheme$b = new Array(3).concat(
      "e7e1efc994c7dd1c77",
      "f1eef6d7b5d8df65b0ce1256",
      "f1eef6d7b5d8df65b0dd1c77980043",
      "f1eef6d4b9dac994c7df65b0dd1c77980043",
      "f1eef6d4b9dac994c7df65b0e7298ace125691003f",
      "f7f4f9e7e1efd4b9dac994c7df65b0e7298ace125691003f",
      "f7f4f9e7e1efd4b9dac994c7df65b0e7298ace125698004367001f"
    ).map(colors);

    var interpolatePuRd = ramp$1(scheme$b);

    var scheme$a = new Array(3).concat(
      "fde0ddfa9fb5c51b8a",
      "feebe2fbb4b9f768a1ae017e",
      "feebe2fbb4b9f768a1c51b8a7a0177",
      "feebe2fcc5c0fa9fb5f768a1c51b8a7a0177",
      "feebe2fcc5c0fa9fb5f768a1dd3497ae017e7a0177",
      "fff7f3fde0ddfcc5c0fa9fb5f768a1dd3497ae017e7a0177",
      "fff7f3fde0ddfcc5c0fa9fb5f768a1dd3497ae017e7a017749006a"
    ).map(colors);

    var interpolateRdPu = ramp$1(scheme$a);

    var scheme$9 = new Array(3).concat(
      "edf8b17fcdbb2c7fb8",
      "ffffcca1dab441b6c4225ea8",
      "ffffcca1dab441b6c42c7fb8253494",
      "ffffccc7e9b47fcdbb41b6c42c7fb8253494",
      "ffffccc7e9b47fcdbb41b6c41d91c0225ea80c2c84",
      "ffffd9edf8b1c7e9b47fcdbb41b6c41d91c0225ea80c2c84",
      "ffffd9edf8b1c7e9b47fcdbb41b6c41d91c0225ea8253494081d58"
    ).map(colors);

    var interpolateYlGnBu = ramp$1(scheme$9);

    var scheme$8 = new Array(3).concat(
      "f7fcb9addd8e31a354",
      "ffffccc2e69978c679238443",
      "ffffccc2e69978c67931a354006837",
      "ffffccd9f0a3addd8e78c67931a354006837",
      "ffffccd9f0a3addd8e78c67941ab5d238443005a32",
      "ffffe5f7fcb9d9f0a3addd8e78c67941ab5d238443005a32",
      "ffffe5f7fcb9d9f0a3addd8e78c67941ab5d238443006837004529"
    ).map(colors);

    var interpolateYlGn = ramp$1(scheme$8);

    var scheme$7 = new Array(3).concat(
      "fff7bcfec44fd95f0e",
      "ffffd4fed98efe9929cc4c02",
      "ffffd4fed98efe9929d95f0e993404",
      "ffffd4fee391fec44ffe9929d95f0e993404",
      "ffffd4fee391fec44ffe9929ec7014cc4c028c2d04",
      "ffffe5fff7bcfee391fec44ffe9929ec7014cc4c028c2d04",
      "ffffe5fff7bcfee391fec44ffe9929ec7014cc4c02993404662506"
    ).map(colors);

    var interpolateYlOrBr = ramp$1(scheme$7);

    var scheme$6 = new Array(3).concat(
      "ffeda0feb24cf03b20",
      "ffffb2fecc5cfd8d3ce31a1c",
      "ffffb2fecc5cfd8d3cf03b20bd0026",
      "ffffb2fed976feb24cfd8d3cf03b20bd0026",
      "ffffb2fed976feb24cfd8d3cfc4e2ae31a1cb10026",
      "ffffccffeda0fed976feb24cfd8d3cfc4e2ae31a1cb10026",
      "ffffccffeda0fed976feb24cfd8d3cfc4e2ae31a1cbd0026800026"
    ).map(colors);

    var interpolateYlOrRd = ramp$1(scheme$6);

    var scheme$5 = new Array(3).concat(
      "deebf79ecae13182bd",
      "eff3ffbdd7e76baed62171b5",
      "eff3ffbdd7e76baed63182bd08519c",
      "eff3ffc6dbef9ecae16baed63182bd08519c",
      "eff3ffc6dbef9ecae16baed64292c62171b5084594",
      "f7fbffdeebf7c6dbef9ecae16baed64292c62171b5084594",
      "f7fbffdeebf7c6dbef9ecae16baed64292c62171b508519c08306b"
    ).map(colors);

    var interpolateBlues = ramp$1(scheme$5);

    var scheme$4 = new Array(3).concat(
      "e5f5e0a1d99b31a354",
      "edf8e9bae4b374c476238b45",
      "edf8e9bae4b374c47631a354006d2c",
      "edf8e9c7e9c0a1d99b74c47631a354006d2c",
      "edf8e9c7e9c0a1d99b74c47641ab5d238b45005a32",
      "f7fcf5e5f5e0c7e9c0a1d99b74c47641ab5d238b45005a32",
      "f7fcf5e5f5e0c7e9c0a1d99b74c47641ab5d238b45006d2c00441b"
    ).map(colors);

    var interpolateGreens = ramp$1(scheme$4);

    var scheme$3 = new Array(3).concat(
      "f0f0f0bdbdbd636363",
      "f7f7f7cccccc969696525252",
      "f7f7f7cccccc969696636363252525",
      "f7f7f7d9d9d9bdbdbd969696636363252525",
      "f7f7f7d9d9d9bdbdbd969696737373525252252525",
      "fffffff0f0f0d9d9d9bdbdbd969696737373525252252525",
      "fffffff0f0f0d9d9d9bdbdbd969696737373525252252525000000"
    ).map(colors);

    var interpolateGreys = ramp$1(scheme$3);

    var scheme$2 = new Array(3).concat(
      "efedf5bcbddc756bb1",
      "f2f0f7cbc9e29e9ac86a51a3",
      "f2f0f7cbc9e29e9ac8756bb154278f",
      "f2f0f7dadaebbcbddc9e9ac8756bb154278f",
      "f2f0f7dadaebbcbddc9e9ac8807dba6a51a34a1486",
      "fcfbfdefedf5dadaebbcbddc9e9ac8807dba6a51a34a1486",
      "fcfbfdefedf5dadaebbcbddc9e9ac8807dba6a51a354278f3f007d"
    ).map(colors);

    var interpolatePurples = ramp$1(scheme$2);

    var scheme$1 = new Array(3).concat(
      "fee0d2fc9272de2d26",
      "fee5d9fcae91fb6a4acb181d",
      "fee5d9fcae91fb6a4ade2d26a50f15",
      "fee5d9fcbba1fc9272fb6a4ade2d26a50f15",
      "fee5d9fcbba1fc9272fb6a4aef3b2ccb181d99000d",
      "fff5f0fee0d2fcbba1fc9272fb6a4aef3b2ccb181d99000d",
      "fff5f0fee0d2fcbba1fc9272fb6a4aef3b2ccb181da50f1567000d"
    ).map(colors);

    var interpolateReds = ramp$1(scheme$1);

    var scheme = new Array(3).concat(
      "fee6cefdae6be6550d",
      "feeddefdbe85fd8d3cd94701",
      "feeddefdbe85fd8d3ce6550da63603",
      "feeddefdd0a2fdae6bfd8d3ce6550da63603",
      "feeddefdd0a2fdae6bfd8d3cf16913d948018c2d04",
      "fff5ebfee6cefdd0a2fdae6bfd8d3cf16913d948018c2d04",
      "fff5ebfee6cefdd0a2fdae6bfd8d3cf16913d94801a636037f2704"
    ).map(colors);

    var interpolateOranges = ramp$1(scheme);

    function interpolateCividis(t) {
      t = Math.max(0, Math.min(1, t));
      return "rgb("
          + Math.max(0, Math.min(255, Math.round(-4.54 - t * (35.34 - t * (2381.73 - t * (6402.7 - t * (7024.72 - t * 2710.57))))))) + ", "
          + Math.max(0, Math.min(255, Math.round(32.49 + t * (170.73 + t * (52.82 - t * (131.46 - t * (176.58 - t * 67.37))))))) + ", "
          + Math.max(0, Math.min(255, Math.round(81.24 + t * (442.36 - t * (2482.43 - t * (6167.24 - t * (6614.94 - t * 2475.67)))))))
          + ")";
    }

    var interpolateCubehelixDefault = cubehelixLong(cubehelix$1(300, 0.5, 0.0), cubehelix$1(-240, 0.5, 1.0));

    var warm = cubehelixLong(cubehelix$1(-100, 0.75, 0.35), cubehelix$1(80, 1.50, 0.8));

    var cool = cubehelixLong(cubehelix$1(260, 0.75, 0.35), cubehelix$1(80, 1.50, 0.8));

    var c$1 = cubehelix$1();

    function interpolateRainbow(t) {
      if (t < 0 || t > 1) t -= Math.floor(t);
      var ts = Math.abs(t - 0.5);
      c$1.h = 360 * t - 100;
      c$1.s = 1.5 - 1.5 * ts;
      c$1.l = 0.8 - 0.9 * ts;
      return c$1 + "";
    }

    var c = rgb(),
        pi_1_3 = Math.PI / 3,
        pi_2_3 = Math.PI * 2 / 3;

    function interpolateSinebow(t) {
      var x;
      t = (0.5 - t) * Math.PI;
      c.r = 255 * (x = Math.sin(t)) * x;
      c.g = 255 * (x = Math.sin(t + pi_1_3)) * x;
      c.b = 255 * (x = Math.sin(t + pi_2_3)) * x;
      return c + "";
    }

    function interpolateTurbo(t) {
      t = Math.max(0, Math.min(1, t));
      return "rgb("
          + Math.max(0, Math.min(255, Math.round(34.61 + t * (1172.33 - t * (10793.56 - t * (33300.12 - t * (38394.49 - t * 14825.05))))))) + ", "
          + Math.max(0, Math.min(255, Math.round(23.31 + t * (557.33 + t * (1225.33 - t * (3574.96 - t * (1073.77 + t * 707.56))))))) + ", "
          + Math.max(0, Math.min(255, Math.round(27.2 + t * (3211.1 - t * (15327.97 - t * (27814 - t * (22569.18 - t * 6838.66)))))))
          + ")";
    }

    function ramp(range) {
      var n = range.length;
      return function(t) {
        return range[Math.max(0, Math.min(n - 1, Math.floor(t * n)))];
      };
    }

    var interpolateViridis = ramp(colors("44015444025645045745055946075a46085c460a5d460b5e470d60470e6147106347116447136548146748166848176948186a481a6c481b6d481c6e481d6f481f70482071482173482374482475482576482677482878482979472a7a472c7a472d7b472e7c472f7d46307e46327e46337f463480453581453781453882443983443a83443b84433d84433e85423f854240864241864142874144874045884046883f47883f48893e49893e4a893e4c8a3d4d8a3d4e8a3c4f8a3c508b3b518b3b528b3a538b3a548c39558c39568c38588c38598c375a8c375b8d365c8d365d8d355e8d355f8d34608d34618d33628d33638d32648e32658e31668e31678e31688e30698e306a8e2f6b8e2f6c8e2e6d8e2e6e8e2e6f8e2d708e2d718e2c718e2c728e2c738e2b748e2b758e2a768e2a778e2a788e29798e297a8e297b8e287c8e287d8e277e8e277f8e27808e26818e26828e26828e25838e25848e25858e24868e24878e23888e23898e238a8d228b8d228c8d228d8d218e8d218f8d21908d21918c20928c20928c20938c1f948c1f958b1f968b1f978b1f988b1f998a1f9a8a1e9b8a1e9c891e9d891f9e891f9f881fa0881fa1881fa1871fa28720a38620a48621a58521a68522a78522a88423a98324aa8325ab8225ac8226ad8127ad8128ae8029af7f2ab07f2cb17e2db27d2eb37c2fb47c31b57b32b67a34b67935b77937b87838b9773aba763bbb753dbc743fbc7340bd7242be7144bf7046c06f48c16e4ac16d4cc26c4ec36b50c46a52c56954c56856c66758c7655ac8645cc8635ec96260ca6063cb5f65cb5e67cc5c69cd5b6ccd5a6ece5870cf5773d05675d05477d1537ad1517cd2507fd34e81d34d84d44b86d54989d5488bd6468ed64590d74393d74195d84098d83e9bd93c9dd93ba0da39a2da37a5db36a8db34aadc32addc30b0dd2fb2dd2db5de2bb8de29bade28bddf26c0df25c2df23c5e021c8e020cae11fcde11dd0e11cd2e21bd5e21ad8e219dae319dde318dfe318e2e418e5e419e7e419eae51aece51befe51cf1e51df4e61ef6e620f8e621fbe723fde725"));

    var magma = ramp(colors("00000401000501010601010802010902020b02020d03030f03031204041405041606051806051a07061c08071e0907200a08220b09240c09260d0a290e0b2b100b2d110c2f120d31130d34140e36150e38160f3b180f3d19103f1a10421c10441d11471e114920114b21114e22115024125325125527125829115a2a115c2c115f2d11612f116331116533106734106936106b38106c390f6e3b0f703d0f713f0f72400f74420f75440f764510774710784910784a10794c117a4e117b4f127b51127c52137c54137d56147d57157e59157e5a167e5c167f5d177f5f187f601880621980641a80651a80671b80681c816a1c816b1d816d1d816e1e81701f81721f817320817521817621817822817922827b23827c23827e24828025828125818326818426818627818827818928818b29818c29818e2a81902a81912b81932b80942c80962c80982d80992d809b2e7f9c2e7f9e2f7fa02f7fa1307ea3307ea5317ea6317da8327daa337dab337cad347cae347bb0357bb2357bb3367ab5367ab73779b83779ba3878bc3978bd3977bf3a77c03a76c23b75c43c75c53c74c73d73c83e73ca3e72cc3f71cd4071cf4070d0416fd2426fd3436ed5446dd6456cd8456cd9466bdb476adc4869de4968df4a68e04c67e24d66e34e65e44f64e55064e75263e85362e95462ea5661eb5760ec5860ed5a5fee5b5eef5d5ef05f5ef1605df2625df2645cf3655cf4675cf4695cf56b5cf66c5cf66e5cf7705cf7725cf8745cf8765cf9785df9795df97b5dfa7d5efa7f5efa815ffb835ffb8560fb8761fc8961fc8a62fc8c63fc8e64fc9065fd9266fd9467fd9668fd9869fd9a6afd9b6bfe9d6cfe9f6dfea16efea36ffea571fea772fea973feaa74feac76feae77feb078feb27afeb47bfeb67cfeb77efeb97ffebb81febd82febf84fec185fec287fec488fec68afec88cfeca8dfecc8ffecd90fecf92fed194fed395fed597fed799fed89afdda9cfddc9efddea0fde0a1fde2a3fde3a5fde5a7fde7a9fde9aafdebacfcecaefceeb0fcf0b2fcf2b4fcf4b6fcf6b8fcf7b9fcf9bbfcfbbdfcfdbf"));

    var inferno = ramp(colors("00000401000501010601010802010a02020c02020e03021004031204031405041706041907051b08051d09061f0a07220b07240c08260d08290e092b10092d110a30120a32140b34150b37160b39180c3c190c3e1b0c411c0c431e0c451f0c48210c4a230c4c240c4f260c51280b53290b552b0b572d0b592f0a5b310a5c320a5e340a5f3609613809623909633b09643d09653e0966400a67420a68440a68450a69470b6a490b6a4a0c6b4c0c6b4d0d6c4f0d6c510e6c520e6d540f6d550f6d57106e59106e5a116e5c126e5d126e5f136e61136e62146e64156e65156e67166e69166e6a176e6c186e6d186e6f196e71196e721a6e741a6e751b6e771c6d781c6d7a1d6d7c1d6d7d1e6d7f1e6c801f6c82206c84206b85216b87216b88226a8a226a8c23698d23698f24699025689225689326679526679727669827669a28659b29649d29649f2a63a02a63a22b62a32c61a52c60a62d60a82e5fa92e5eab2f5ead305dae305cb0315bb1325ab3325ab43359b63458b73557b93556ba3655bc3754bd3853bf3952c03a51c13a50c33b4fc43c4ec63d4dc73e4cc83f4bca404acb4149cc4248ce4347cf4446d04545d24644d34743d44842d54a41d74b3fd84c3ed94d3dda4e3cdb503bdd513ade5238df5337e05536e15635e25734e35933e45a31e55c30e65d2fe75e2ee8602de9612bea632aeb6429eb6628ec6726ed6925ee6a24ef6c23ef6e21f06f20f1711ff1731df2741cf3761bf37819f47918f57b17f57d15f67e14f68013f78212f78410f8850ff8870ef8890cf98b0bf98c0af98e09fa9008fa9207fa9407fb9606fb9706fb9906fb9b06fb9d07fc9f07fca108fca309fca50afca60cfca80dfcaa0ffcac11fcae12fcb014fcb216fcb418fbb61afbb81dfbba1ffbbc21fbbe23fac026fac228fac42afac62df9c72ff9c932f9cb35f8cd37f8cf3af7d13df7d340f6d543f6d746f5d949f5db4cf4dd4ff4df53f4e156f3e35af3e55df2e661f2e865f2ea69f1ec6df1ed71f1ef75f1f179f2f27df2f482f3f586f3f68af4f88ef5f992f6fa96f8fb9af9fc9dfafda1fcffa4"));

    var plasma = ramp(colors("0d088710078813078916078a19068c1b068d1d068e20068f2206902406912605912805922a05932c05942e05952f059631059733059735049837049938049a3a049a3c049b3e049c3f049c41049d43039e44039e46039f48039f4903a04b03a14c02a14e02a25002a25102a35302a35502a45601a45801a45901a55b01a55c01a65e01a66001a66100a76300a76400a76600a76700a86900a86a00a86c00a86e00a86f00a87100a87201a87401a87501a87701a87801a87a02a87b02a87d03a87e03a88004a88104a78305a78405a78606a68707a68808a68a09a58b0aa58d0ba58e0ca48f0da4910ea3920fa39410a29511a19613a19814a099159f9a169f9c179e9d189d9e199da01a9ca11b9ba21d9aa31e9aa51f99a62098a72197a82296aa2395ab2494ac2694ad2793ae2892b02991b12a90b22b8fb32c8eb42e8db52f8cb6308bb7318ab83289ba3388bb3488bc3587bd3786be3885bf3984c03a83c13b82c23c81c33d80c43e7fc5407ec6417dc7427cc8437bc9447aca457acb4679cc4778cc4977cd4a76ce4b75cf4c74d04d73d14e72d24f71d35171d45270d5536fd5546ed6556dd7566cd8576bd9586ada5a6ada5b69db5c68dc5d67dd5e66de5f65de6164df6263e06363e16462e26561e26660e3685fe4695ee56a5de56b5de66c5ce76e5be76f5ae87059e97158e97257ea7457eb7556eb7655ec7754ed7953ed7a52ee7b51ef7c51ef7e50f07f4ff0804ef1814df1834cf2844bf3854bf3874af48849f48948f58b47f58c46f68d45f68f44f79044f79143f79342f89441f89540f9973ff9983ef99a3efa9b3dfa9c3cfa9e3bfb9f3afba139fba238fca338fca537fca636fca835fca934fdab33fdac33fdae32fdaf31fdb130fdb22ffdb42ffdb52efeb72dfeb82cfeba2cfebb2bfebd2afebe2afec029fdc229fdc328fdc527fdc627fdc827fdca26fdcb26fccd25fcce25fcd025fcd225fbd324fbd524fbd724fad824fada24f9dc24f9dd25f8df25f8e125f7e225f7e425f6e626f6e826f5e926f5eb27f4ed27f3ee27f3f027f2f227f1f426f1f525f0f724f0f921"));

    const baseDefaults = {
        position: 'chartArea',
        property: 'value',
        grid: {
            z: 1,
            drawOnChartArea: false,
        },
        ticks: {
            z: 1,
        },
        legend: {
            align: 'right',
            position: 'bottom-right',
            length: 100,
            width: 50,
            margin: 8,
            indicatorWidth: 10,
        },
    };
    function computeLegendMargin(legend) {
        const { indicatorWidth, align: pos, margin } = legend;
        const left = (typeof margin === 'number' ? margin : margin.left) + (pos === 'right' ? indicatorWidth : 0);
        const top = (typeof margin === 'number' ? margin : margin.top) + (pos === 'bottom' ? indicatorWidth : 0);
        const right = (typeof margin === 'number' ? margin : margin.right) + (pos === 'left' ? indicatorWidth : 0);
        const bottom = (typeof margin === 'number' ? margin : margin.bottom) + (pos === 'top' ? indicatorWidth : 0);
        return { left, top, right, bottom };
    }
    function computeLegendPosition(chartArea, legend, width, height, legendSize) {
        const { indicatorWidth, align: axisPos, position: pos } = legend;
        const isHor = axisPos === 'top' || axisPos === 'bottom';
        const w = (axisPos === 'left' ? legendSize.w : width) + (isHor ? indicatorWidth : 0);
        const h = (axisPos === 'top' ? legendSize.h : height) + (!isHor ? indicatorWidth : 0);
        const margin = computeLegendMargin(legend);
        if (typeof pos === 'string') {
            switch (pos) {
                case 'top-left':
                    return [margin.left, margin.top];
                case 'top':
                    return [(chartArea.right - w) / 2, margin.top];
                case 'left':
                    return [margin.left, (chartArea.bottom - h) / 2];
                case 'top-right':
                    return [chartArea.right - w - margin.right, margin.top];
                case 'bottom-right':
                    return [chartArea.right - w - margin.right, chartArea.bottom - h - margin.bottom];
                case 'bottom':
                    return [(chartArea.right - w) / 2, chartArea.bottom - h - margin.bottom];
                case 'bottom-left':
                    return [margin.left, chartArea.bottom - h - margin.bottom];
                default:
                    return [chartArea.right - w - margin.right, (chartArea.bottom - h) / 2];
            }
        }
        return [pos.x, pos.y];
    }
    class LegendScale extends chart_js.LinearScale {
        constructor() {
            super(...arguments);
            this.legendSize = { w: 0, h: 0 };
        }
        init(options) {
            options.position = 'chartArea';
            super.init(options);
            this.axis = 'r';
        }
        parse(raw, index) {
            if (raw && typeof raw[this.options.property] === 'number') {
                return raw[this.options.property];
            }
            return super.parse(raw, index);
        }
        isHorizontal() {
            return this.options.legend.align === 'top' || this.options.legend.align === 'bottom';
        }
        _getNormalizedValue(v) {
            if (v == null || Number.isNaN(v)) {
                return null;
            }
            return (v - this._startValue) / this._valueRange;
        }
        update(maxWidth, maxHeight, margins) {
            const ch = Math.min(maxHeight, this.bottom == null ? Number.POSITIVE_INFINITY : this.bottom);
            const cw = Math.min(maxWidth, this.right == null ? Number.POSITIVE_INFINITY : this.right);
            const l = this.options.legend;
            const isHor = this.isHorizontal();
            const factor = (v, full) => (v < 1 ? full * v : v);
            const w = Math.min(cw, factor(isHor ? l.length : l.width, cw)) - (!isHor ? l.indicatorWidth : 0);
            const h = Math.min(ch, factor(!isHor ? l.length : l.width, ch)) - (isHor ? l.indicatorWidth : 0);
            this.legendSize = { w, h };
            this.bottom = h;
            this.height = h;
            this.right = w;
            this.width = w;
            const bak = this.options.position;
            this.options.position = this.options.legend.align;
            const r = super.update(w, h, margins);
            this.options.position = bak;
            this.height = Math.min(h, this.height);
            this.width = Math.min(w, this.width);
            return r;
        }
        _computeLabelArea() {
            return undefined;
        }
        draw(chartArea) {
            if (!this._isVisible()) {
                return;
            }
            const pos = computeLegendPosition(chartArea, this.options.legend, this.width, this.height, this.legendSize);
            const { ctx } = this;
            ctx.save();
            ctx.translate(pos[0], pos[1]);
            const bak = this.options.position;
            this.options.position = this.options.legend.align;
            super.draw({ ...chartArea, bottom: this.height + 10, right: this.width });
            this.options.position = bak;
            const { indicatorWidth } = this.options.legend;
            switch (this.options.legend.align) {
                case 'left':
                    ctx.translate(this.legendSize.w, 0);
                    break;
                case 'top':
                    ctx.translate(0, this.legendSize.h);
                    break;
                case 'bottom':
                    ctx.translate(0, -indicatorWidth);
                    break;
                default:
                    ctx.translate(-indicatorWidth, 0);
                    break;
            }
            this._drawIndicator();
            ctx.restore();
        }
        _drawIndicator() {
        }
    }
    class LogarithmicLegendScale extends chart_js.LogarithmicScale {
        constructor() {
            super(...arguments);
            this.legendSize = { w: 0, h: 0 };
        }
        init(options) {
            LegendScale.prototype.init.call(this, options);
        }
        parse(raw, index) {
            return LegendScale.prototype.parse.call(this, raw, index);
        }
        isHorizontal() {
            return this.options.legend.align === 'top' || this.options.legend.align === 'bottom';
        }
        _getNormalizedValue(v) {
            if (v == null || Number.isNaN(v)) {
                return null;
            }
            return (Math.log10(v) - this._startValue) / this._valueRange;
        }
        update(maxWidth, maxHeight, margins) {
            return LegendScale.prototype.update.call(this, maxWidth, maxHeight, margins);
        }
        _computeLabelArea() {
            return undefined;
        }
        draw(chartArea) {
            return LegendScale.prototype.draw.call(this, chartArea);
        }
        _drawIndicator() {
        }
    }

    const lookup = {
        interpolateBlues,
        interpolateBrBG,
        interpolateBuGn,
        interpolateBuPu,
        interpolateCividis,
        interpolateCool: cool,
        interpolateCubehelixDefault,
        interpolateGnBu,
        interpolateGreens,
        interpolateGreys,
        interpolateInferno: inferno,
        interpolateMagma: magma,
        interpolateOrRd,
        interpolateOranges,
        interpolatePRGn,
        interpolatePiYG,
        interpolatePlasma: plasma,
        interpolatePuBu,
        interpolatePuBuGn,
        interpolatePuOr,
        interpolatePuRd,
        interpolatePurples,
        interpolateRainbow,
        interpolateRdBu,
        interpolateRdGy,
        interpolateRdPu,
        interpolateRdYlBu,
        interpolateRdYlGn,
        interpolateReds,
        interpolateSinebow,
        interpolateSpectral,
        interpolateTurbo,
        interpolateViridis,
        interpolateWarm: warm,
        interpolateYlGn,
        interpolateYlGnBu,
        interpolateYlOrBr,
        interpolateYlOrRd,
    };
    Object.keys(lookup).forEach((key) => {
        lookup[`${key.charAt(11).toLowerCase()}${key.slice(12)}`] = lookup[key];
        lookup[key.slice(11)] = lookup[key];
    });
    function quantize$1(v, steps) {
        const perStep = 1 / steps;
        if (v <= perStep) {
            return 0;
        }
        if (v >= 1 - perStep) {
            return 1;
        }
        for (let acc = 0; acc < 1; acc += perStep) {
            if (v < acc) {
                return acc - perStep / 2;
            }
        }
        return v;
    }
    const colorScaleDefaults = {
        interpolate: 'blues',
        missing: 'transparent',
        quantize: 0,
    };
    class ColorScale extends LegendScale {
        get interpolate() {
            const o = this.options;
            if (!o) {
                return (v) => `rgb(${v},${v},${v})`;
            }
            if (typeof o.interpolate === 'function') {
                return o.interpolate;
            }
            return lookup[o.interpolate] || lookup.blues;
        }
        getColorForValue(value) {
            const v = this._getNormalizedValue(value);
            if (v == null || Number.isNaN(v)) {
                return this.options.missing;
            }
            return this.getColor(v);
        }
        getColor(normalized) {
            let v = normalized;
            if (this.options.quantize > 0) {
                v = quantize$1(v, this.options.quantize);
            }
            return this.interpolate(v);
        }
        _drawIndicator() {
            const { indicatorWidth: indicatorSize } = this.options.legend;
            const reverse = this._reversePixels;
            if (this.isHorizontal()) {
                const w = this.width;
                if (this.options.quantize > 0) {
                    const stepWidth = w / this.options.quantize;
                    const offset = !reverse ? (i) => i : (i) => w - stepWidth - i;
                    for (let i = 0; i < w; i += stepWidth) {
                        const v = (i + stepWidth / 2) / w;
                        this.ctx.fillStyle = this.getColor(v);
                        this.ctx.fillRect(offset(i), 0, stepWidth, indicatorSize);
                    }
                }
                else {
                    const offset = !reverse ? (i) => i : (i) => w - 1 - i;
                    for (let i = 0; i < w; i += 1) {
                        this.ctx.fillStyle = this.getColor((i + 0.5) / w);
                        this.ctx.fillRect(offset(i), 0, 1, indicatorSize);
                    }
                }
            }
            else {
                const h = this.height;
                if (this.options.quantize > 0) {
                    const stepWidth = h / this.options.quantize;
                    const offset = !reverse ? (i) => i : (i) => h - stepWidth - i;
                    for (let i = 0; i < h; i += stepWidth) {
                        const v = (i + stepWidth / 2) / h;
                        this.ctx.fillStyle = this.getColor(v);
                        this.ctx.fillRect(0, offset(i), indicatorSize, stepWidth);
                    }
                }
                else {
                    const offset = !reverse ? (i) => i : (i) => h - 1 - i;
                    for (let i = 0; i < h; i += 1) {
                        this.ctx.fillStyle = this.getColor((i + 0.5) / h);
                        this.ctx.fillRect(0, offset(i), indicatorSize, 1);
                    }
                }
            }
        }
    }
    ColorScale.id = 'color';
    ColorScale.defaults = helpers.merge({}, [chart_js.LinearScale.defaults, baseDefaults, colorScaleDefaults]);
    ColorScale.descriptors = {
        _scriptable: (name) => name !== 'interpolate',
        _indexable: false,
    };
    class ColorLogarithmicScale extends LogarithmicLegendScale {
        constructor() {
            super(...arguments);
            this.interpolate = (v) => `rgb(${v},${v},${v})`;
        }
        init(options) {
            super.init(options);
            if (typeof options.interpolate === 'function') {
                this.interpolate = options.interpolate;
            }
            else {
                this.interpolate = lookup[options.interpolate] || lookup.blues;
            }
        }
        getColorForValue(value) {
            return ColorScale.prototype.getColorForValue.call(this, value);
        }
        getColor(normalized) {
            let v = normalized;
            if (this.options.quantize > 0) {
                v = quantize$1(v, this.options.quantize);
            }
            return this.interpolate(v);
        }
        _drawIndicator() {
            return ColorScale.prototype._drawIndicator.call(this);
        }
    }
    ColorLogarithmicScale.id = 'colorLogarithmic';
    ColorLogarithmicScale.defaults = helpers.merge({}, [
        chart_js.LogarithmicScale.defaults,
        baseDefaults,
        colorScaleDefaults,
    ]);
    ColorLogarithmicScale.descriptors = {
        _scriptable: (name) => name !== 'interpolate',
        _indexable: false,
    };

    const scaleDefaults = {
        missing: 1,
        mode: 'area',
        range: [2, 20],
        legend: {
            align: 'bottom',
            length: 90,
            width: 70,
            indicatorWidth: 42,
        },
    };
    class SizeScale extends LegendScale {
        constructor() {
            super(...arguments);
            this._model = null;
        }
        getSizeForValue(value) {
            const v = this._getNormalizedValue(value);
            if (v == null || Number.isNaN(v)) {
                return this.options.missing;
            }
            return this.getSizeImpl(v);
        }
        getSizeImpl(normalized) {
            const [r0, r1] = this.options.range;
            if (this.options.mode === 'area') {
                const a1 = r1 * r1 * Math.PI;
                const a0 = r0 * r0 * Math.PI;
                const range = a1 - a0;
                const a = normalized * range + a0;
                return Math.sqrt(a / Math.PI);
            }
            const range = r1 - r0;
            return normalized * range + r0;
        }
        _drawIndicator() {
            const { ctx } = this;
            const shift = this.options.legend.indicatorWidth / 2;
            const isHor = this.isHorizontal();
            const values = this.ticks;
            const labelItems = this.getLabelItems();
            const positions = labelItems
                ? labelItems.map((el) => ({ [isHor ? 'x' : 'y']: el.options.translation[isHor ? 0 : 1] }))
                : values.map((_, i) => ({ [isHor ? 'x' : 'y']: this.getPixelForTick(i) }));
            (this._gridLineItems || []).forEach((item) => {
                ctx.save();
                ctx.strokeStyle = item.color;
                ctx.lineWidth = item.width;
                if (ctx.setLineDash) {
                    ctx.setLineDash(item.borderDash);
                    ctx.lineDashOffset = item.borderDashOffset;
                }
                ctx.beginPath();
                if (this.options.grid.drawTicks) {
                    switch (this.options.legend.align) {
                        case 'left':
                            ctx.moveTo(0, item.ty1);
                            ctx.lineTo(shift, item.ty2);
                            break;
                        case 'top':
                            ctx.moveTo(item.tx1, 0);
                            ctx.lineTo(item.tx2, shift);
                            break;
                        case 'bottom':
                            ctx.moveTo(item.tx1, shift);
                            ctx.lineTo(item.tx2, shift * 2);
                            break;
                        default:
                            ctx.moveTo(shift, item.ty1);
                            ctx.lineTo(shift * 2, item.ty2);
                            break;
                    }
                }
                ctx.stroke();
                ctx.restore();
            });
            if (this._model) {
                const props = this._model;
                ctx.strokeStyle = props.borderColor;
                ctx.lineWidth = props.borderWidth || 0;
                ctx.fillStyle = props.backgroundColor;
            }
            else {
                ctx.fillStyle = 'blue';
            }
            values.forEach((v, i) => {
                const pos = positions[i];
                const radius = this.getSizeForValue(v.value);
                const x = isHor ? pos.x : shift;
                const y = isHor ? shift : pos.y;
                const renderOptions = {
                    pointStyle: 'circle',
                    borderWidth: 0,
                    ...(this._model || {}),
                    radius,
                };
                helpers.drawPoint(ctx, renderOptions, x, y);
            });
        }
    }
    SizeScale.id = 'size';
    SizeScale.defaults = helpers.merge({}, [chart_js.LinearScale.defaults, baseDefaults, scaleDefaults]);
    SizeScale.descriptors = {
        _scriptable: true,
        _indexable: (name) => name !== 'range',
    };
    class SizeLogarithmicScale extends LogarithmicLegendScale {
        constructor() {
            super(...arguments);
            this._model = null;
        }
        getSizeForValue(value) {
            const v = this._getNormalizedValue(value);
            if (v == null || Number.isNaN(v)) {
                return this.options.missing;
            }
            return this.getSizeImpl(v);
        }
        getSizeImpl(normalized) {
            return SizeScale.prototype.getSizeImpl.call(this, normalized);
        }
        _drawIndicator() {
            SizeScale.prototype._drawIndicator.call(this);
        }
    }
    SizeLogarithmicScale.id = 'sizeLogarithmic';
    SizeLogarithmicScale.defaults = helpers.merge({}, [chart_js.LogarithmicScale.defaults, baseDefaults, scaleDefaults]);

    function growGeoBounds(bounds, amount) {
        return [
            [bounds[0][0] - amount, bounds[0][1] - amount],
            [bounds[1][0] + amount, bounds[1][1] + amount],
        ];
    }
    class GeoFeature extends chart_js.Element {
        constructor() {
            super(...arguments);
            this.cache = undefined;
        }
        inRange(mouseX, mouseY) {
            const bb = this.getBounds();
            const r = (Number.isNaN(mouseX) || (mouseX >= bb.x && mouseX <= bb.x2)) &&
                (Number.isNaN(mouseY) || (mouseY >= bb.y && mouseY <= bb.y2));
            const projection = this.projectionScale.geoPath.projection();
            if (r && !Number.isNaN(mouseX) && !Number.isNaN(mouseY) && typeof projection.invert === 'function') {
                const longLat = projection.invert([mouseX, mouseY]);
                return longLat != null && geoContains(this.feature, longLat);
            }
            return r;
        }
        inXRange(mouseX) {
            return this.inRange(mouseX, Number.NaN);
        }
        inYRange(mouseY) {
            return this.inRange(Number.NaN, mouseY);
        }
        getCenterPoint() {
            if (this.cache && this.cache.center) {
                return this.cache.center;
            }
            let center;
            if (this.center) {
                const p = this.projectionScale.projection([this.center.longitude, this.center.latitude]);
                center = {
                    x: p[0],
                    y: p[1],
                };
            }
            else {
                const centroid = this.projectionScale.geoPath.centroid(this.feature);
                center = {
                    x: centroid[0],
                    y: centroid[1],
                };
            }
            this.cache = { ...(this.cache || {}), center };
            return center;
        }
        getBounds() {
            if (this.cache && this.cache.bounds) {
                return this.cache.bounds;
            }
            const bb = growGeoBounds(this.projectionScale.geoPath.bounds(this.feature), this.options.borderWidth / 2);
            const bounds = {
                x: bb[0][0],
                x2: bb[1][0],
                y: bb[0][1],
                y2: bb[1][1],
                width: bb[1][0] - bb[0][0],
                height: bb[1][1] - bb[0][1],
            };
            this.cache = { ...(this.cache || {}), bounds };
            return bounds;
        }
        _drawInCache(doc) {
            const bounds = this.getBounds();
            if (!Number.isFinite(bounds.x)) {
                return;
            }
            const canvas = this.cache && this.cache.canvas ? this.cache.canvas : doc.createElement('canvas');
            const x1 = Math.floor(bounds.x);
            const y1 = Math.floor(bounds.y);
            const x2 = Math.ceil(bounds.x + bounds.width);
            const y2 = Math.ceil(bounds.y + bounds.height);
            const pixelRatio = this.pixelRatio || 1;
            const width = Math.ceil(Math.max(x2 - x1, 1) * pixelRatio);
            const height = Math.ceil(Math.max(y2 - y1, 1) * pixelRatio);
            if (width <= 0 || height <= 0) {
                return;
            }
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.save();
                ctx.scale(pixelRatio, pixelRatio);
                ctx.translate(-x1, -y1);
                this._drawImpl(ctx);
                ctx.restore();
                this.cache = { ...(this.cache || {}), canvas, canvasKey: this._optionsToKey() };
            }
        }
        _optionsToKey() {
            const { options } = this;
            return `${options.backgroundColor};${options.borderColor};${options.borderWidth};${this.pixelRatio}`;
        }
        _drawImpl(ctx) {
            const { feature } = this;
            const { options } = this;
            ctx.beginPath();
            this.projectionScale.geoPath.context(ctx)(feature);
            if (options.backgroundColor) {
                ctx.fillStyle = options.backgroundColor;
                ctx.fill();
            }
            if (options.borderColor) {
                ctx.strokeStyle = options.borderColor;
                ctx.lineWidth = options.borderWidth;
                ctx.stroke();
            }
        }
        draw(ctx) {
            const { feature } = this;
            if (!feature) {
                return;
            }
            if ((!this.cache || this.cache.canvasKey !== this._optionsToKey()) && ctx.canvas.ownerDocument != null) {
                this._drawInCache(ctx.canvas.ownerDocument);
            }
            const bounds = this.getBounds();
            if (this.cache && this.cache.canvas && this.cache.canvas.width > 0 && this.cache.canvas.height > 0) {
                const x1 = Math.floor(bounds.x);
                const y1 = Math.floor(bounds.y);
                const x2 = Math.ceil(bounds.x + bounds.width);
                const y2 = Math.ceil(bounds.y + bounds.height);
                const width = x2 - x1;
                const height = y2 - y1;
                if (width > 0 && height > 0) {
                    ctx.drawImage(this.cache.canvas, x1, y1, x2 - x1, y2 - y1);
                }
            }
            else if (Number.isFinite(bounds.x)) {
                ctx.save();
                this._drawImpl(ctx);
                ctx.restore();
            }
        }
    }
    GeoFeature.id = 'geoFeature';
    GeoFeature.defaults = {
        ...chart_js.BarElement.defaults,
        outlineBackgroundColor: null,
        outlineBorderWidth: 0,
        graticuleBorderColor: '#CCCCCC',
        graticuleBorderWidth: 0,
    };
    GeoFeature.defaultRoutes = {
        outlineBorderColor: 'borderColor',
        ...(chart_js.BarElement.defaultRoutes || {}),
    };

    const geoDefaults = {
        showOutline: false,
        showGraticule: false,
        clipMap: true,
    };
    const geoOverrides = {
        scales: {
            projection: {
                axis: 'x',
                type: ProjectionScale.id,
                position: 'chartArea',
                display: false,
            },
        },
    };
    function patchDatasetElementOptions(options) {
        const r = { ...options };
        Object.keys(options).forEach((key) => {
            let targetKey = key;
            if (key.startsWith('outline')) {
                const sub = key.slice('outline'.length);
                targetKey = sub[0].toLowerCase() + sub.slice(1);
            }
            else if (key.startsWith('hoverOutline')) {
                targetKey = `hover${key.slice('hoverOutline'.length)}`;
            }
            else {
                return;
            }
            delete r[key];
            r[targetKey] = options[key];
        });
        return r;
    }
    class GeoController extends chart_js.DatasetController {
        getGeoDataset() {
            return super.getDataset();
        }
        getGeoOptions() {
            return this.chart.options;
        }
        getProjectionScale() {
            return this.getScaleForId('projection');
        }
        linkScales() {
            const dataset = this.getGeoDataset();
            const meta = this.getMeta();
            meta.xAxisID = 'projection';
            dataset.xAxisID = 'projection';
            meta.yAxisID = 'projection';
            dataset.yAxisID = 'projection';
            meta.xScale = this.getScaleForId('projection');
            meta.yScale = this.getScaleForId('projection');
            this.getProjectionScale().computeBounds(this.resolveOutline());
        }
        showOutline() {
            return helpers.valueOrDefault(this.getGeoDataset().showOutline, this.getGeoOptions().showOutline);
        }
        clipMap() {
            return helpers.valueOrDefault(this.getGeoDataset().clipMap, this.getGeoOptions().clipMap);
        }
        getGraticule() {
            return helpers.valueOrDefault(this.getGeoDataset().showGraticule, this.getGeoOptions().showGraticule);
        }
        update(mode) {
            super.update(mode);
            const meta = this.getMeta();
            const scale = this.getProjectionScale();
            const dirtyCache = scale.updateBounds();
            if (this.showOutline()) {
                const elem = meta.dataset;
                if (dirtyCache) {
                    delete elem.cache;
                }
                elem.projectionScale = scale;
                elem.pixelRatio = this.chart.currentDevicePixelRatio;
                if (mode !== 'resize') {
                    const options = patchDatasetElementOptions(this.resolveDatasetElementOptions(mode));
                    const properties = {
                        feature: this.resolveOutline(),
                        options,
                    };
                    this.updateElement(elem, undefined, properties, mode);
                    if (this.getGraticule()) {
                        meta.graticule = options;
                    }
                }
            }
            else if (this.getGraticule() && mode !== 'resize') {
                meta.graticule = patchDatasetElementOptions(this.resolveDatasetElementOptions(mode));
            }
            this.updateElements(meta.data, 0, meta.data.length, mode);
            if (dirtyCache) {
                meta.data.forEach((elem) => delete elem.cache);
            }
        }
        resolveOutline() {
            const ds = this.getGeoDataset();
            const outline = ds.outline || { type: 'Sphere' };
            if (Array.isArray(outline)) {
                return {
                    type: 'FeatureCollection',
                    features: outline,
                };
            }
            return outline;
        }
        showGraticule() {
            const g = this.getGraticule();
            const options = this.getMeta().graticule;
            if (!g || !options) {
                return;
            }
            const { ctx } = this.chart;
            const scale = this.getProjectionScale();
            const path = scale.geoPath.context(ctx);
            ctx.save();
            ctx.beginPath();
            if (typeof g === 'boolean') {
                if (g) {
                    path(graticule10());
                }
            }
            else {
                const geo = graticule();
                if (g.stepMajor) {
                    geo.stepMajor(g.stepMajor);
                }
                if (g.stepMinor) {
                    geo.stepMinor(g.stepMinor);
                }
                path(geo());
            }
            ctx.strokeStyle = options.graticuleBorderColor;
            ctx.lineWidth = options.graticuleBorderWidth;
            ctx.stroke();
            ctx.restore();
        }
        draw() {
            const { chart } = this;
            const clipMap = this.clipMap();
            let enabled = false;
            if (clipMap === true || clipMap === 'outline' || clipMap === 'outline+graticule') {
                enabled = true;
                helpers.clipArea(chart.ctx, chart.chartArea);
            }
            if (this.showOutline() && this.getMeta().dataset) {
                this.getMeta().dataset.draw.call(this.getMeta().dataset, chart.ctx, chart.chartArea);
            }
            if (clipMap === true || clipMap === 'graticule' || clipMap === 'outline+graticule') {
                if (!enabled) {
                    helpers.clipArea(chart.ctx, chart.chartArea);
                }
            }
            else if (enabled) {
                enabled = false;
                helpers.unclipArea(chart.ctx);
            }
            this.showGraticule();
            if (clipMap === true || clipMap === 'items') {
                if (!enabled) {
                    helpers.clipArea(chart.ctx, chart.chartArea);
                }
            }
            else if (enabled) {
                enabled = false;
                helpers.unclipArea(chart.ctx);
            }
            this.getMeta().data.forEach((elem) => elem.draw.call(elem, chart.ctx, chart.chartArea));
            if (enabled) {
                enabled = false;
                helpers.unclipArea(chart.ctx);
            }
        }
    }

    function patchController(type, config, controller, elements = [], scales = []) {
        chart_js.registry.addControllers(controller);
        if (Array.isArray(elements)) {
            chart_js.registry.addElements(...elements);
        }
        else {
            chart_js.registry.addElements(elements);
        }
        if (Array.isArray(scales)) {
            chart_js.registry.addScales(...scales);
        }
        else {
            chart_js.registry.addScales(scales);
        }
        const c = config;
        c.type = type;
        return c;
    }

    class ChoroplethController extends GeoController {
        initialize() {
            super.initialize();
            this.enableOptionSharing = true;
        }
        linkScales() {
            super.linkScales();
            const dataset = this.getGeoDataset();
            const meta = this.getMeta();
            meta.vAxisID = 'color';
            meta.rAxisID = 'color';
            dataset.vAxisID = 'color';
            dataset.rAxisID = 'color';
            meta.rScale = this.getScaleForId('color');
            meta.vScale = meta.rScale;
            meta.iScale = meta.xScale;
            meta.iAxisID = meta.xAxisID;
            dataset.iAxisID = meta.xAxisID;
        }
        _getOtherScale(scale) {
            return scale;
        }
        parse(start, count) {
            const rScale = this.getMeta().rScale;
            const { data } = this.getDataset();
            const meta = this._cachedMeta;
            for (let i = start; i < start + count; i += 1) {
                meta._parsed[i] = {
                    [rScale.axis]: rScale.parse(data[i], i),
                };
            }
        }
        updateElements(elems, start, count, mode) {
            const firstOpts = this.resolveDataElementOptions(start, mode);
            const sharedOptions = this.getSharedOptions(firstOpts);
            const includeOptions = this.includeOptions(mode, sharedOptions);
            const scale = this.getProjectionScale();
            this.updateSharedOptions(sharedOptions, mode, firstOpts);
            for (let i = start; i < start + count; i += 1) {
                const elem = elems[i];
                elem.projectionScale = scale;
                elem.feature = this._data[i].feature;
                elem.center = this._data[i].center;
                elem.pixelRatio = this.chart.currentDevicePixelRatio;
                const center = elem.getCenterPoint();
                const properties = {
                    x: center.x,
                    y: center.y,
                };
                if (includeOptions) {
                    properties.options = (sharedOptions || this.resolveDataElementOptions(i, mode));
                }
                this.updateElement(elem, i, properties, mode);
            }
        }
        indexToColor(index) {
            const rScale = this.getMeta().rScale;
            return rScale.getColorForValue(this.getParsed(index)[rScale.axis]);
        }
    }
    ChoroplethController.id = 'choropleth';
    ChoroplethController.defaults = helpers.merge({}, [
        geoDefaults,
        {
            datasetElementType: GeoFeature.id,
            dataElementType: GeoFeature.id,
        },
    ]);
    ChoroplethController.overrides = helpers.merge({}, [
        geoOverrides,
        {
            plugins: {
                tooltip: {
                    callbacks: {
                        title() {
                            return '';
                        },
                        label(item) {
                            var _a, _b, _c, _d;
                            if (item.formattedValue == null) {
                                return (_b = (_a = item.chart.data) === null || _a === void 0 ? void 0 : _a.labels) === null || _b === void 0 ? void 0 : _b[item.dataIndex];
                            }
                            return `${(_d = (_c = item.chart.data) === null || _c === void 0 ? void 0 : _c.labels) === null || _d === void 0 ? void 0 : _d[item.dataIndex]}: ${item.formattedValue}`;
                        },
                    },
                },
                colors: {
                    enabled: false,
                },
            },
            scales: {
                color: {
                    type: ColorScale.id,
                    axis: 'x',
                },
            },
            elements: {
                geoFeature: {
                    backgroundColor(context) {
                        if (context.dataIndex == null) {
                            return null;
                        }
                        const controller = context.chart.getDatasetMeta(context.datasetIndex)
                            .controller;
                        return controller.indexToColor(context.dataIndex);
                    },
                },
            },
        },
    ]);
    class ChoroplethChart extends chart_js.Chart {
        constructor(item, config) {
            super(item, patchController('choropleth', config, ChoroplethController, GeoFeature, [ColorScale, ProjectionScale]));
        }
    }
    ChoroplethChart.id = ChoroplethController.id;

    class BubbleMapController extends GeoController {
        initialize() {
            super.initialize();
            this.enableOptionSharing = true;
        }
        linkScales() {
            super.linkScales();
            const dataset = this.getGeoDataset();
            const meta = this.getMeta();
            meta.vAxisID = 'size';
            meta.rAxisID = 'size';
            dataset.vAxisID = 'size';
            dataset.rAxisID = 'size';
            meta.rScale = this.getScaleForId('size');
            meta.vScale = meta.rScale;
            meta.iScale = meta.xScale;
            meta.iAxisID = meta.xAxisID;
            dataset.iAxisID = meta.xAxisID;
        }
        _getOtherScale(scale) {
            return scale;
        }
        parse(start, count) {
            const rScale = this.getMeta().rScale;
            const data = this.getDataset().data;
            const meta = this._cachedMeta;
            for (let i = start; i < start + count; i += 1) {
                const d = data[i];
                meta._parsed[i] = {
                    x: d.longitude == null ? d.x : d.longitude,
                    y: d.latitude == null ? d.y : d.latitude,
                    [rScale.axis]: rScale.parse(d, i),
                };
            }
        }
        updateElements(elems, start, count, mode) {
            const reset = mode === 'reset';
            const firstOpts = this.resolveDataElementOptions(start, mode);
            const sharedOptions = this.getSharedOptions(firstOpts);
            const includeOptions = this.includeOptions(mode, sharedOptions);
            const scale = this.getProjectionScale();
            this.getMeta().rScale._model = firstOpts;
            this.updateSharedOptions(sharedOptions, mode, firstOpts);
            for (let i = start; i < start + count; i += 1) {
                const elem = elems[i];
                const parsed = this.getParsed(i);
                const projection = scale.projection([parsed.x, parsed.y]);
                const properties = {
                    x: projection ? projection[0] : 0,
                    y: projection ? projection[1] : 0,
                    skip: Number.isNaN(parsed.x) || Number.isNaN(parsed.y),
                };
                if (includeOptions) {
                    properties.options = (sharedOptions || this.resolveDataElementOptions(i, mode));
                    if (reset) {
                        properties.options.radius = 0;
                    }
                }
                this.updateElement(elem, i, properties, mode);
            }
        }
        indexToRadius(index) {
            const rScale = this.getMeta().rScale;
            return rScale.getSizeForValue(this.getParsed(index)[rScale.axis]);
        }
    }
    BubbleMapController.id = 'bubbleMap';
    BubbleMapController.defaults = helpers.merge({}, [
        geoDefaults,
        {
            dataElementType: chart_js.PointElement.id,
            datasetElementType: GeoFeature.id,
            showOutline: true,
            clipMap: 'outline+graticule',
        },
    ]);
    BubbleMapController.overrides = helpers.merge({}, [
        geoOverrides,
        {
            plugins: {
                tooltip: {
                    callbacks: {
                        title() {
                            return '';
                        },
                        label(item) {
                            var _a, _b, _c, _d;
                            if (item.formattedValue == null) {
                                return (_b = (_a = item.chart.data) === null || _a === void 0 ? void 0 : _a.labels) === null || _b === void 0 ? void 0 : _b[item.dataIndex];
                            }
                            return `${(_d = (_c = item.chart.data) === null || _c === void 0 ? void 0 : _c.labels) === null || _d === void 0 ? void 0 : _d[item.dataIndex]}: ${item.formattedValue}`;
                        },
                    },
                },
            },
            scales: {
                size: {
                    axis: 'x',
                    type: SizeScale.id,
                },
            },
            elements: {
                point: {
                    radius(context) {
                        if (context.dataIndex == null) {
                            return null;
                        }
                        const controller = context.chart.getDatasetMeta(context.datasetIndex)
                            .controller;
                        return controller.indexToRadius(context.dataIndex);
                    },
                    hoverRadius(context) {
                        if (context.dataIndex == null) {
                            return null;
                        }
                        const controller = context.chart.getDatasetMeta(context.datasetIndex)
                            .controller;
                        return controller.indexToRadius(context.dataIndex) + 1;
                    },
                },
            },
        },
    ]);
    class BubbleMapChart extends chart_js.Chart {
        constructor(item, config) {
            super(item, patchController('bubbleMap', config, BubbleMapController, GeoFeature, [SizeScale, ProjectionScale]));
        }
    }
    BubbleMapChart.id = BubbleMapController.id;

    function identity(x) {
      return x;
    }

    function transform(transform) {
      if (transform == null) return identity;
      var x0,
          y0,
          kx = transform.scale[0],
          ky = transform.scale[1],
          dx = transform.translate[0],
          dy = transform.translate[1];
      return function(input, i) {
        if (!i) x0 = y0 = 0;
        var j = 2, n = input.length, output = new Array(n);
        output[0] = (x0 += input[0]) * kx + dx;
        output[1] = (y0 += input[1]) * ky + dy;
        while (j < n) output[j] = input[j], ++j;
        return output;
      };
    }

    function bbox(topology) {
      var t = transform(topology.transform), key,
          x0 = Infinity, y0 = x0, x1 = -x0, y1 = -x0;

      function bboxPoint(p) {
        p = t(p);
        if (p[0] < x0) x0 = p[0];
        if (p[0] > x1) x1 = p[0];
        if (p[1] < y0) y0 = p[1];
        if (p[1] > y1) y1 = p[1];
      }

      function bboxGeometry(o) {
        switch (o.type) {
          case "GeometryCollection": o.geometries.forEach(bboxGeometry); break;
          case "Point": bboxPoint(o.coordinates); break;
          case "MultiPoint": o.coordinates.forEach(bboxPoint); break;
        }
      }

      topology.arcs.forEach(function(arc) {
        var i = -1, n = arc.length, p;
        while (++i < n) {
          p = t(arc[i], i);
          if (p[0] < x0) x0 = p[0];
          if (p[0] > x1) x1 = p[0];
          if (p[1] < y0) y0 = p[1];
          if (p[1] > y1) y1 = p[1];
        }
      });

      for (key in topology.objects) {
        bboxGeometry(topology.objects[key]);
      }

      return [x0, y0, x1, y1];
    }

    function reverse(array, n) {
      var t, j = array.length, i = j - n;
      while (i < --j) t = array[i], array[i++] = array[j], array[j] = t;
    }

    function feature(topology, o) {
      if (typeof o === "string") o = topology.objects[o];
      return o.type === "GeometryCollection"
          ? {type: "FeatureCollection", features: o.geometries.map(function(o) { return feature$1(topology, o); })}
          : feature$1(topology, o);
    }

    function feature$1(topology, o) {
      var id = o.id,
          bbox = o.bbox,
          properties = o.properties == null ? {} : o.properties,
          geometry = object(topology, o);
      return id == null && bbox == null ? {type: "Feature", properties: properties, geometry: geometry}
          : bbox == null ? {type: "Feature", id: id, properties: properties, geometry: geometry}
          : {type: "Feature", id: id, bbox: bbox, properties: properties, geometry: geometry};
    }

    function object(topology, o) {
      var transformPoint = transform(topology.transform),
          arcs = topology.arcs;

      function arc(i, points) {
        if (points.length) points.pop();
        for (var a = arcs[i < 0 ? ~i : i], k = 0, n = a.length; k < n; ++k) {
          points.push(transformPoint(a[k], k));
        }
        if (i < 0) reverse(points, n);
      }

      function point(p) {
        return transformPoint(p);
      }

      function line(arcs) {
        var points = [];
        for (var i = 0, n = arcs.length; i < n; ++i) arc(arcs[i], points);
        if (points.length < 2) points.push(points[0]); // This should never happen per the specification.
        return points;
      }

      function ring(arcs) {
        var points = line(arcs);
        while (points.length < 4) points.push(points[0]); // This may happen if an arc has only two points.
        return points;
      }

      function polygon(arcs) {
        return arcs.map(ring);
      }

      function geometry(o) {
        var type = o.type, coordinates;
        switch (type) {
          case "GeometryCollection": return {type: type, geometries: o.geometries.map(geometry)};
          case "Point": coordinates = point(o.coordinates); break;
          case "MultiPoint": coordinates = o.coordinates.map(point); break;
          case "LineString": coordinates = line(o.arcs); break;
          case "MultiLineString": coordinates = o.arcs.map(line); break;
          case "Polygon": coordinates = polygon(o.arcs); break;
          case "MultiPolygon": coordinates = o.arcs.map(polygon); break;
          default: return null;
        }
        return {type: type, coordinates: coordinates};
      }

      return geometry(o);
    }

    function stitch(topology, arcs) {
      var stitchedArcs = {},
          fragmentByStart = {},
          fragmentByEnd = {},
          fragments = [],
          emptyIndex = -1;

      // Stitch empty arcs first, since they may be subsumed by other arcs.
      arcs.forEach(function(i, j) {
        var arc = topology.arcs[i < 0 ? ~i : i], t;
        if (arc.length < 3 && !arc[1][0] && !arc[1][1]) {
          t = arcs[++emptyIndex], arcs[emptyIndex] = i, arcs[j] = t;
        }
      });

      arcs.forEach(function(i) {
        var e = ends(i),
            start = e[0],
            end = e[1],
            f, g;

        if (f = fragmentByEnd[start]) {
          delete fragmentByEnd[f.end];
          f.push(i);
          f.end = end;
          if (g = fragmentByStart[end]) {
            delete fragmentByStart[g.start];
            var fg = g === f ? f : f.concat(g);
            fragmentByStart[fg.start = f.start] = fragmentByEnd[fg.end = g.end] = fg;
          } else {
            fragmentByStart[f.start] = fragmentByEnd[f.end] = f;
          }
        } else if (f = fragmentByStart[end]) {
          delete fragmentByStart[f.start];
          f.unshift(i);
          f.start = start;
          if (g = fragmentByEnd[start]) {
            delete fragmentByEnd[g.end];
            var gf = g === f ? f : g.concat(f);
            fragmentByStart[gf.start = g.start] = fragmentByEnd[gf.end = f.end] = gf;
          } else {
            fragmentByStart[f.start] = fragmentByEnd[f.end] = f;
          }
        } else {
          f = [i];
          fragmentByStart[f.start = start] = fragmentByEnd[f.end = end] = f;
        }
      });

      function ends(i) {
        var arc = topology.arcs[i < 0 ? ~i : i], p0 = arc[0], p1;
        if (topology.transform) p1 = [0, 0], arc.forEach(function(dp) { p1[0] += dp[0], p1[1] += dp[1]; });
        else p1 = arc[arc.length - 1];
        return i < 0 ? [p1, p0] : [p0, p1];
      }

      function flush(fragmentByEnd, fragmentByStart) {
        for (var k in fragmentByEnd) {
          var f = fragmentByEnd[k];
          delete fragmentByStart[f.start];
          delete f.start;
          delete f.end;
          f.forEach(function(i) { stitchedArcs[i < 0 ? ~i : i] = 1; });
          fragments.push(f);
        }
      }

      flush(fragmentByEnd, fragmentByStart);
      flush(fragmentByStart, fragmentByEnd);
      arcs.forEach(function(i) { if (!stitchedArcs[i < 0 ? ~i : i]) fragments.push([i]); });

      return fragments;
    }

    function mesh(topology) {
      return object(topology, meshArcs.apply(this, arguments));
    }

    function meshArcs(topology, object, filter) {
      var arcs, i, n;
      if (arguments.length > 1) arcs = extractArcs(topology, object, filter);
      else for (i = 0, arcs = new Array(n = topology.arcs.length); i < n; ++i) arcs[i] = i;
      return {type: "MultiLineString", arcs: stitch(topology, arcs)};
    }

    function extractArcs(topology, object, filter) {
      var arcs = [],
          geomsByArc = [],
          geom;

      function extract0(i) {
        var j = i < 0 ? ~i : i;
        (geomsByArc[j] || (geomsByArc[j] = [])).push({i: i, g: geom});
      }

      function extract1(arcs) {
        arcs.forEach(extract0);
      }

      function extract2(arcs) {
        arcs.forEach(extract1);
      }

      function extract3(arcs) {
        arcs.forEach(extract2);
      }

      function geometry(o) {
        switch (geom = o, o.type) {
          case "GeometryCollection": o.geometries.forEach(geometry); break;
          case "LineString": extract1(o.arcs); break;
          case "MultiLineString": case "Polygon": extract2(o.arcs); break;
          case "MultiPolygon": extract3(o.arcs); break;
        }
      }

      geometry(object);

      geomsByArc.forEach(filter == null
          ? function(geoms) { arcs.push(geoms[0].i); }
          : function(geoms) { if (filter(geoms[0].g, geoms[geoms.length - 1].g)) arcs.push(geoms[0].i); });

      return arcs;
    }

    function planarRingArea(ring) {
      var i = -1, n = ring.length, a, b = ring[n - 1], area = 0;
      while (++i < n) a = b, b = ring[i], area += a[0] * b[1] - a[1] * b[0];
      return Math.abs(area); // Note: doubled area!
    }

    function merge(topology) {
      return object(topology, mergeArcs.apply(this, arguments));
    }

    function mergeArcs(topology, objects) {
      var polygonsByArc = {},
          polygons = [],
          groups = [];

      objects.forEach(geometry);

      function geometry(o) {
        switch (o.type) {
          case "GeometryCollection": o.geometries.forEach(geometry); break;
          case "Polygon": extract(o.arcs); break;
          case "MultiPolygon": o.arcs.forEach(extract); break;
        }
      }

      function extract(polygon) {
        polygon.forEach(function(ring) {
          ring.forEach(function(arc) {
            (polygonsByArc[arc = arc < 0 ? ~arc : arc] || (polygonsByArc[arc] = [])).push(polygon);
          });
        });
        polygons.push(polygon);
      }

      function area(ring) {
        return planarRingArea(object(topology, {type: "Polygon", arcs: [ring]}).coordinates[0]);
      }

      polygons.forEach(function(polygon) {
        if (!polygon._) {
          var group = [],
              neighbors = [polygon];
          polygon._ = 1;
          groups.push(group);
          while (polygon = neighbors.pop()) {
            group.push(polygon);
            polygon.forEach(function(ring) {
              ring.forEach(function(arc) {
                polygonsByArc[arc < 0 ? ~arc : arc].forEach(function(polygon) {
                  if (!polygon._) {
                    polygon._ = 1;
                    neighbors.push(polygon);
                  }
                });
              });
            });
          }
        }
      });

      polygons.forEach(function(polygon) {
        delete polygon._;
      });

      return {
        type: "MultiPolygon",
        arcs: groups.map(function(polygons) {
          var arcs = [], n;

          // Extract the exterior (unique) arcs.
          polygons.forEach(function(polygon) {
            polygon.forEach(function(ring) {
              ring.forEach(function(arc) {
                if (polygonsByArc[arc < 0 ? ~arc : arc].length < 2) {
                  arcs.push(arc);
                }
              });
            });
          });

          // Stitch the arcs into one or more rings.
          arcs = stitch(topology, arcs);

          // If more than one ring is returned,
          // at most one of these rings can be the exterior;
          // choose the one with the greatest absolute area.
          if ((n = arcs.length) > 1) {
            for (var i = 1, k = area(arcs[0]), ki, t; i < n; ++i) {
              if ((ki = area(arcs[i])) > k) {
                t = arcs[0], arcs[0] = arcs[i], arcs[i] = t, k = ki;
              }
            }
          }

          return arcs;
        }).filter(function(arcs) {
          return arcs.length > 0;
        })
      };
    }

    function bisect(a, x) {
      var lo = 0, hi = a.length;
      while (lo < hi) {
        var mid = lo + hi >>> 1;
        if (a[mid] < x) lo = mid + 1;
        else hi = mid;
      }
      return lo;
    }

    function neighbors(objects) {
      var indexesByArc = {}, // arc index -> array of object indexes
          neighbors = objects.map(function() { return []; });

      function line(arcs, i) {
        arcs.forEach(function(a) {
          if (a < 0) a = ~a;
          var o = indexesByArc[a];
          if (o) o.push(i);
          else indexesByArc[a] = [i];
        });
      }

      function polygon(arcs, i) {
        arcs.forEach(function(arc) { line(arc, i); });
      }

      function geometry(o, i) {
        if (o.type === "GeometryCollection") o.geometries.forEach(function(o) { geometry(o, i); });
        else if (o.type in geometryType) geometryType[o.type](o.arcs, i);
      }

      var geometryType = {
        LineString: line,
        MultiLineString: polygon,
        Polygon: polygon,
        MultiPolygon: function(arcs, i) { arcs.forEach(function(arc) { polygon(arc, i); }); }
      };

      objects.forEach(geometry);

      for (var i in indexesByArc) {
        for (var indexes = indexesByArc[i], m = indexes.length, j = 0; j < m; ++j) {
          for (var k = j + 1; k < m; ++k) {
            var ij = indexes[j], ik = indexes[k], n;
            if ((n = neighbors[ij])[i = bisect(n, ik)] !== ik) n.splice(i, 0, ik);
            if ((n = neighbors[ik])[i = bisect(n, ij)] !== ij) n.splice(i, 0, ij);
          }
        }
      }

      return neighbors;
    }

    function untransform(transform) {
      if (transform == null) return identity;
      var x0,
          y0,
          kx = transform.scale[0],
          ky = transform.scale[1],
          dx = transform.translate[0],
          dy = transform.translate[1];
      return function(input, i) {
        if (!i) x0 = y0 = 0;
        var j = 2,
            n = input.length,
            output = new Array(n),
            x1 = Math.round((input[0] - dx) / kx),
            y1 = Math.round((input[1] - dy) / ky);
        output[0] = x1 - x0, x0 = x1;
        output[1] = y1 - y0, y0 = y1;
        while (j < n) output[j] = input[j], ++j;
        return output;
      };
    }

    function quantize(topology, transform) {
      if (topology.transform) throw new Error("already quantized");

      if (!transform || !transform.scale) {
        if (!((n = Math.floor(transform)) >= 2)) throw new Error("n must be ≥2");
        box = topology.bbox || bbox(topology);
        var x0 = box[0], y0 = box[1], x1 = box[2], y1 = box[3], n;
        transform = {scale: [x1 - x0 ? (x1 - x0) / (n - 1) : 1, y1 - y0 ? (y1 - y0) / (n - 1) : 1], translate: [x0, y0]};
      } else {
        box = topology.bbox;
      }

      var t = untransform(transform), box, key, inputs = topology.objects, outputs = {};

      function quantizePoint(point) {
        return t(point);
      }

      function quantizeGeometry(input) {
        var output;
        switch (input.type) {
          case "GeometryCollection": output = {type: "GeometryCollection", geometries: input.geometries.map(quantizeGeometry)}; break;
          case "Point": output = {type: "Point", coordinates: quantizePoint(input.coordinates)}; break;
          case "MultiPoint": output = {type: "MultiPoint", coordinates: input.coordinates.map(quantizePoint)}; break;
          default: return input;
        }
        if (input.id != null) output.id = input.id;
        if (input.bbox != null) output.bbox = input.bbox;
        if (input.properties != null) output.properties = input.properties;
        return output;
      }

      function quantizeArc(input) {
        var i = 0, j = 1, n = input.length, p, output = new Array(n); // pessimistic
        output[0] = t(input[0], 0);
        while (++i < n) if ((p = t(input[i], i))[0] || p[1]) output[j++] = p; // non-coincident points
        if (j === 1) output[j++] = [0, 0]; // an arc must have at least two points
        output.length = j;
        return output;
      }

      for (key in inputs) outputs[key] = quantizeGeometry(inputs[key]);

      return {
        type: "Topology",
        bbox: box,
        transform: transform,
        objects: outputs,
        arcs: topology.arcs.map(quantizeArc)
      };
    }

    var index = /*#__PURE__*/Object.freeze({
      __proto__: null,
      bbox: bbox,
      feature: feature,
      merge: merge,
      mergeArcs: mergeArcs,
      mesh: mesh,
      meshArcs: meshArcs,
      neighbors: neighbors,
      quantize: quantize,
      transform: transform,
      untransform: untransform
    });

    chart_js.registry.addScales(ColorLogarithmicScale, SizeLogarithmicScale, ProjectionScale, ColorScale, SizeScale);
    chart_js.registry.addElements(GeoFeature);
    chart_js.registry.addControllers(ChoroplethController, BubbleMapController);

    exports.BubbleMapChart = BubbleMapChart;
    exports.BubbleMapController = BubbleMapController;
    exports.ChoroplethChart = ChoroplethChart;
    exports.ChoroplethController = ChoroplethController;
    exports.ColorLogarithmicScale = ColorLogarithmicScale;
    exports.ColorScale = ColorScale;
    exports.GeoController = GeoController;
    exports.GeoFeature = GeoFeature;
    exports.ProjectionScale = ProjectionScale;
    exports.SizeLogarithmicScale = SizeLogarithmicScale;
    exports.SizeScale = SizeScale;
    exports.geoAlbers = geoAlbers;
    exports.geoAlbersUsa = geoAlbersUsa;
    exports.geoAzimuthalEqualArea = geoAzimuthalEqualArea;
    exports.geoAzimuthalEquidistant = geoAzimuthalEquidistant;
    exports.geoConicConformal = geoConicConformal;
    exports.geoConicEqualArea = geoConicEqualArea;
    exports.geoConicEquidistant = geoConicEquidistant;
    exports.geoEqualEarth = geoEqualEarth;
    exports.geoEquirectangular = geoEquirectangular;
    exports.geoGnomonic = geoGnomonic;
    exports.geoMercator = geoMercator;
    exports.geoNaturalEarth1 = geoNaturalEarth1;
    exports.geoOrthographic = geoOrthographic;
    exports.geoStereographic = geoStereographic;
    exports.geoTransverseMercator = geoTransverseMercator;
    exports.topojson = index;

  }));
  //# sourceMappingURL=index.umd.js.map
