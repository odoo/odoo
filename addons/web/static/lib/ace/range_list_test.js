/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

if (typeof process !== "undefined") {
    require("amd-loader");
}

define(function(require, exports, module) {
"use strict";

var Range = require("./range").Range;
var RangeList = require("./range_list").RangeList;
var EditSession = require("./edit_session").EditSession;
var assert = require("./test/assertions");

function flatten(rangeList) {
    var points = [];
    rangeList.ranges.forEach(function(r) {
        points.push(r.start.row, r.start.column, r.end.row, r.end.column)
    })
    return points;
}
function testRangeList(rangeList, points) {
    assert.equal("" + flatten(rangeList), "" + points);
}

module.exports = {

    name: "ACE range_list.js",

    "test: rangeList pointIndex": function() {
        var rangeList = new RangeList();
        rangeList.ranges = [
            new Range(1,2,3,4),
            new Range(4,2,5,4),
            new Range(8,8,9,9)
        ];

        assert.equal(rangeList.pointIndex({row: 0, column: 1}), -1);
        assert.equal(rangeList.pointIndex({row: 1, column: 2}), 0);
        assert.equal(rangeList.pointIndex({row: 1, column: 3}), 0);
        assert.equal(rangeList.pointIndex({row: 3, column: 4}), 0);
        assert.equal(rangeList.pointIndex({row: 4, column: 1}), -2);
        assert.equal(rangeList.pointIndex({row: 5, column: 1}), 1);
        assert.equal(rangeList.pointIndex({row: 8, column: 9}), 2);
        assert.equal(rangeList.pointIndex({row: 18, column: 9}), -4);
    },
    
    "test: rangeList pointIndex excludeEdges": function() {
        var rangeList = new RangeList();
        rangeList.ranges = [
            new Range(1,2,3,4),
            new Range(4,2,5,4),
            new Range(8,8,9,9),
            new Range(10,10,10,10)
        ];

        assert.equal(rangeList.pointIndex({row: 0, column: 1}, true), -1);
        assert.equal(rangeList.pointIndex({row: 1, column: 2}, true), -1);
        assert.equal(rangeList.pointIndex({row: 1, column: 3}, true), 0);
        assert.equal(rangeList.pointIndex({row: 3, column: 4}, true), -2);
        assert.equal(rangeList.pointIndex({row: 4, column: 1}, true), -2);
        assert.equal(rangeList.pointIndex({row: 5, column: 1}, true), 1);
        assert.equal(rangeList.pointIndex({row: 8, column: 9}, true), 2);
        assert.equal(rangeList.pointIndex({row: 10, column: 10}, true), 3);
        assert.equal(rangeList.pointIndex({row: 18, column: 9}, true), -5);
    },

    "test: rangeList add": function() {
        var rangeList = new RangeList();
        rangeList.addList([
            new Range(9,0,9,1),
            new Range(1,2,3,4),
            new Range(8,8,9,9),
            new Range(4,2,5,4),
            new Range(3,20,3,24),
            new Range(6,6,7,7)
        ]);
        assert.equal(rangeList.ranges.length, 5);

        rangeList.add(new Range(1,2,3,5));
        assert.range(rangeList.ranges[0], 1,2,3,5);
        assert.equal(rangeList.ranges.length, 5);

        rangeList.add(new Range(7,7,7,7));
        assert.range(rangeList.ranges[3], 7,7,7,7);
        rangeList.add(new Range(7,8,7,8));
        assert.range(rangeList.ranges[4], 7,8,7,8);
    },

    "test: rangeList add empty": function() {
        var rangeList = new RangeList();
        rangeList.addList([
            new Range(7,10,7,10),
            new Range(9,10,9,10),
            new Range(8,10,8,10)
        ]);
        assert.equal(rangeList.ranges.length, 3);

        rangeList.add(new Range(9,10,9,10));
        testRangeList(rangeList, [7,10,7,10,8,10,8,10,9,10,9,10]);
    },

    "test: rangeList merge": function() {
        var rangeList = new RangeList();
        rangeList.addList([
            new Range(1,2,3,4),
            new Range(4,2,5,4),
            new Range(6,6,7,7),
            new Range(8,8,9,9)
        ]);
        var removed = [];

        assert.equal(rangeList.ranges.length, 4);

        rangeList.ranges[1].end.row = 7;
        removed = rangeList.merge();
        assert.equal(removed.length, 1);
        assert.range(rangeList.ranges[1], 4,2,7,7);
        assert.equal(rangeList.ranges.length, 3);

        rangeList.ranges[0].end.row = 10;
        removed = rangeList.merge();
        assert.range(rangeList.ranges[0], 1,2,10,4);
        assert.equal(removed.length, 2);
        assert.equal(rangeList.ranges.length, 1);

        rangeList.ranges.push(new Range(10,10,10,10));
        rangeList.ranges.push(new Range(10,10,10,10));
        removed = rangeList.merge();
        assert.equal(rangeList.ranges.length, 2);
    },

    "test: rangeList remove": function() {
        var rangeList = new RangeList();
        var list = [
            new Range(1,2,3,4),
            new Range(4,2,5,4),
            new Range(6,6,7,7),
            new Range(8,8,9,9)
        ];
        rangeList.addList(list);
        assert.equal(rangeList.ranges.length, 4);
        rangeList.substractPoint({row: 1, column: 2});
        assert.equal(rangeList.ranges.length, 3);
        rangeList.substractPoint({row: 6, column: 7});
        assert.equal(rangeList.ranges.length, 2);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
