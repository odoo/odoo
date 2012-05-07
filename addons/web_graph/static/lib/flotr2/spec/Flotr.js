describe('Flotr', function () {

  describe('Plots', function () {

    var
      nodeA, nodeB,
      a, b;

    beforeEach(function () {

      // Add imagediff matchers
      this.addMatchers(imagediff.jasmine);

      nodeA = buildNode();
      nodeB = buildNode();
    });

    afterEach(function () {
      destroyNode(nodeA);
      destroyNode(nodeB);
      a = null;
      b = null;
      Flotr = null;
    });

    _.each(TestFlotr.ExampleList.examples, function (example, key) {

      it('should draw a `' + example.name + '`line graph', function () {

        executeExampleTest(example, StableFlotr, nodeA);
        executeExampleTest(example, TestFlotr, nodeB);

        if (example.timeout) {
          waits(example.timeout);
          runs (function () {
            expect(nodeB.graph.ctx).toImageDiffEqual(nodeA.graph.ctx, example.tolerance || 0);
          });
        } else {
          expect(nodeB.graph.ctx).toImageDiffEqual(nodeA.graph.ctx, example.tolerance || 0);
        }
      });
    });

    // Helpers

    function executeExampleTest (example, flotr, node) {
      Math.seedrandom(example.key);
      Flotr = flotr;
      example.callback.apply(this, [node].concat(example.args || []));
    }

    function buildNode () {
      var node = document.createElement('div');
      document.body.appendChild(node);
      node.style.width = '320px';
      node.style.height = '240px';
      return node;
    }

    function destroyNode (node) {
      document.body.removeChild(node);
    }
  });

  describe('Main', function () {

    it('gets a tick size', function () {
      expect(TestFlotr.getTickSize).not.toBeUndefined();
      expect(TestFlotr.getTickSize(10, 0, 100, 1)).toEqual(10);
      expect(TestFlotr.getTickSize(20, 0, 100, 1)).toEqual(5);
      expect(TestFlotr.getTickSize(5, 10, 110, 1)).toEqual(20);
      expect(TestFlotr.getTickSize(0, 0, 10, 1)).toEqual(Number.POSITIVE_INFINITY);
      expect(isNaN(TestFlotr.getTickSize(0, 0, -10, 1))).toBeTruthy();
    });
  });
});
